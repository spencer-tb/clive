FROM golang:1.23-alpine AS builder
WORKDIR /app
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 go build -o hapi .

FROM alpine:3.20
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/hapi /usr/local/bin/
EXPOSE 8080
ENTRYPOINT ["hapi"]
