package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sort"
	"strings"
	"sync"
	"time"
)

// Store fetches and caches hive test results from the static file server.
type Store struct {
	baseURL string
	groups  []string

	mu       sync.RWMutex
	listings map[string][]TestRun // group -> all listing entries (sorted newest first)
	latest   map[string][]TestRun // group -> latest run per (client, simulator)

	detailsMu sync.RWMutex
	details   map[string]*SuiteResult // "group/fileName" -> cached detail

	client *http.Client
}

func NewStore(baseURL string, groups []string) *Store {
	s := &Store{
		baseURL:  strings.TrimRight(baseURL, "/"),
		listings: make(map[string][]TestRun),
		latest:   make(map[string][]TestRun),
		details:  make(map[string]*SuiteResult),
		client:   &http.Client{Timeout: 120 * time.Second},
	}
	if len(groups) > 0 {
		s.groups = groups
	}
	return s
}

// Start discovers groups (if not set), performs an initial refresh, then refreshes periodically.
func (s *Store) Start(refreshInterval time.Duration) {
	if len(s.groups) == 0 {
		discovered, err := s.discoverGroups()
		if err != nil {
			log.Fatalf("failed to discover groups: %v", err)
		}
		s.groups = discovered
		log.Printf("discovered groups: %v", s.groups)
	}
	s.refresh()
	go func() {
		ticker := time.NewTicker(refreshInterval)
		defer ticker.Stop()
		for range ticker.C {
			// Re-discover groups on each refresh in case new ones are added.
			if discovered, err := s.discoverGroups(); err == nil && len(discovered) > 0 {
				s.mu.Lock()
				s.groups = discovered
				s.mu.Unlock()
			}
			s.refresh()
		}
	}()
}

// discoverGroups fetches discovery.json from the base URL to find available groups.
func (s *Store) discoverGroups() ([]string, error) {
	url := s.baseURL + "/discovery.json"
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("GET %s: status %d", url, resp.StatusCode)
	}

	var entries []struct {
		Name string `json:"name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&entries); err != nil {
		return nil, fmt.Errorf("decode %s: %w", url, err)
	}

	groups := make([]string, 0, len(entries))
	for _, e := range entries {
		if e.Name != "" {
			groups = append(groups, e.Name)
		}
	}
	return groups, nil
}

func (s *Store) refresh() {
	s.mu.RLock()
	groups := make([]string, len(s.groups))
	copy(groups, s.groups)
	s.mu.RUnlock()

	for _, group := range groups {
		runs, err := s.fetchListing(group)
		if err != nil {
			log.Printf("error fetching listing for %s: %v", group, err)
			continue
		}

		sort.Slice(runs, func(i, j int) bool {
			return runs[i].Start.After(runs[j].Start)
		})

		latest := findLatestRuns(runs)

		s.mu.Lock()
		s.listings[group] = runs
		s.latest[group] = latest
		s.mu.Unlock()

		// Pre-fetch detail files for latest runs in parallel.
		var wg sync.WaitGroup
		for _, run := range latest {
			if run.Fails == 0 {
				continue
			}
			wg.Add(1)
			go func(r TestRun) {
				defer wg.Done()
				if _, err := s.GetDetail(group, r.FileName); err != nil {
					log.Printf("error pre-fetching %s/%s: %v", group, r.FileName, err)
				}
			}(run)
		}
		wg.Wait()

		// Evict cached details for runs no longer in the listing.
		validFiles := make(map[string]bool, len(runs))
		for _, run := range runs {
			validFiles[group+"/"+run.FileName] = true
		}
		s.detailsMu.Lock()
		for key := range s.details {
			if strings.HasPrefix(key, group+"/") && !validFiles[key] {
				delete(s.details, key)
			}
		}
		s.detailsMu.Unlock()

		log.Printf("refreshed %s: %d total runs, %d latest", group, len(runs), len(latest))
	}
}

// findLatestRuns returns the most recent run for each unique (simulator, client) pair.
// Input must be sorted newest-first.
func findLatestRuns(runs []TestRun) []TestRun {
	seen := make(map[string]bool)
	var latest []TestRun
	for _, run := range runs {
		hasNew := false
		for _, client := range run.Clients {
			if !seen[run.Name+"/"+client] {
				hasNew = true
			}
		}
		if hasNew {
			for _, client := range run.Clients {
				seen[run.Name+"/"+client] = true
			}
			latest = append(latest, run)
		}
	}
	return latest
}

func (s *Store) fetchListing(group string) ([]TestRun, error) {
	url := fmt.Sprintf("%s/%s/listing.jsonl", s.baseURL, group)
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("GET %s: status %d", url, resp.StatusCode)
	}

	var runs []TestRun
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 1<<20), 1<<20) // 1MB line buffer
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var run TestRun
		if err := json.Unmarshal([]byte(line), &run); err != nil {
			log.Printf("skipping malformed line in %s listing: %v", group, err)
			continue
		}
		runs = append(runs, run)
	}
	return runs, scanner.Err()
}

// GetDetail returns the cached suite detail, fetching it if not cached.
func (s *Store) GetDetail(group, fileName string) (*SuiteResult, error) {
	key := group + "/" + fileName

	s.detailsMu.RLock()
	if detail, ok := s.details[key]; ok {
		s.detailsMu.RUnlock()
		return detail, nil
	}
	s.detailsMu.RUnlock()

	url := fmt.Sprintf("%s/%s/results/%s", s.baseURL, group, fileName)
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("GET %s: status %d", url, resp.StatusCode)
	}

	var detail SuiteResult
	if err := json.NewDecoder(resp.Body).Decode(&detail); err != nil {
		return nil, fmt.Errorf("decode %s: %w", url, err)
	}

	s.detailsMu.Lock()
	s.details[key] = &detail
	s.detailsMu.Unlock()

	return &detail, nil
}

// FetchLog fetches a log file and returns the bytes in [begin, end).
func (s *Store) FetchLog(group, logPath string, begin, end int64) (string, error) {
	url := fmt.Sprintf("%s/%s/results/%s", s.baseURL, group, logPath)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	// Try HTTP Range request for efficiency.
	if begin >= 0 && end > begin {
		req.Header.Set("Range", fmt.Sprintf("bytes=%d-%d", begin, end-1))
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("GET %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 206 {
		return "", fmt.Errorf("GET %s: status %d", url, resp.StatusCode)
	}

	const maxLogSize = 50 << 20 // 50 MB
	data, err := io.ReadAll(io.LimitReader(resp.Body, maxLogSize))
	if err != nil {
		return "", err
	}

	// If we got a full response instead of a range, slice manually.
	if resp.StatusCode == 200 && begin >= 0 && end > begin && end <= int64(len(data)) {
		return string(data[begin:end]), nil
	}

	return string(data), nil
}

func (s *Store) GetLatestRuns(group string) ([]TestRun, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	runs, ok := s.latest[group]
	return runs, ok
}

func (s *Store) GetAllRuns(group string) ([]TestRun, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	runs, ok := s.listings[group]
	return runs, ok
}

func (s *Store) GetGroups() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	groups := make([]string, len(s.groups))
	copy(groups, s.groups)
	return groups
}
