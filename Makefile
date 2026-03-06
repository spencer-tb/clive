.PHONY: build clean release

VERSION ?= dev

build:
	go build -o hapi .
	go build -o clive ./cmd/hive-cli/

clean:
	rm -f hapi clive clive-*

release:
	GOOS=linux  GOARCH=amd64 go build -ldflags="-s -w" -o dist/clive-linux-amd64   ./cmd/hive-cli/
	GOOS=linux  GOARCH=arm64 go build -ldflags="-s -w" -o dist/clive-linux-arm64   ./cmd/hive-cli/
	GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o dist/clive-darwin-amd64  ./cmd/hive-cli/
	GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o dist/clive-darwin-arm64  ./cmd/hive-cli/
