# linkme

A customizable link page generator built in Go.

![A screenshot of the application.](assets/screenshot.png)

## Usage

```bash
# Build the static site
go run ./cmd/linkme build

# Serve locally
go run ./cmd/linkme serve
```

## Docker

```bash
docker run -d -p 8080:80 ghcr.io/ironicbadger/linkme:latest
```

## Configuration

Edit `config/config.yaml` to customize your links and appearance.

### Analytics

Supported: Google Analytics, GoatCounter, and Plausible.

Example config:

```yaml
analytics:
  google:
    id: "G-XXXXXXX"
  goatcounter:
    id: "example"
    selfhosted: false
  plausible:
    domain: "example.com" # tracked site
    script_url: "" # optional; set to your self-hosted instance URL (e.g. https://plausible.example.com/js/script.js)
```

GoatCounter:
If `selfhosted: true`, `id` must be the full host (FQDN) of your instance. Otherwise `id` is used as the subdomain on `goatcounter.com`.

Plausible:
Set `domain` to the site you want to track. For self-hosted, set `script_url` to your instance’s script URL.
