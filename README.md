# LingXiFox Apps

Source for **https://apps.lingxifox.cn**, the LingXiFox software hub. The first product is **Texel (纹粒)**, a local HEIC texture tool for iPhone.

The site is a static, four-language marketing and support site. It has no client-side JavaScript, no backend, no database, no third-party analytics, and no tracking. All pages are generated from Python content dictionaries and plain HTML/CSS.

## Live

- Production domain: <https://apps.lingxifox.cn/> (live; custom domain active)
- Cloudflare Pages: <https://lingxifox-apps.pages.dev/>
- Repository: <https://github.com/LingXiFox/apps-site>

## Pages

| Route | Page |
| --- | --- |
| `/` | Software hub |
| `/texel/` | Texel product page |
| `/texel/privacy/` | Texel privacy policy |
| `/texel/support/` | Texel support and FAQ |

Every route exists in four languages:

| Language | Prefix |
| --- | --- |
| Simplified Chinese (default) | `/` |
| Traditional Chinese | `/zh-Hant/` |
| English | `/en/` |
| Japanese | `/ja/` |

## Stack

- Python 3.11+ standard library only for the build.
- Hand-written HTML and CSS. No runtime framework, no bundler, no npm dependency for the site itself.
- Cloudflare Pages, Direct Upload deployment.
- Optional: Pillow only when regenerating `assets/og.png`; it is not needed to build the site.

## Structure

```
apps-site/
├── assets/               # icons, OG image, styles.css
├── content/              # one Python dict per language
│   ├── zh_hans.py
│   ├── zh_hant.py
│   ├── en.py
│   └── ja.py
├── .github/workflows/
│   └── deploy.yml        # build, verify, deploy on push to main
├── scripts/
│   ├── build.py          # static generator + link/content validation
│   ├── blake3.py         # dependency-free BLAKE3 used by Pages uploads
│   ├── deploy_pages.py   # Cloudflare Pages Direct Upload API client
│   └── deploy.sh         # local build and deploy wrapper
├── dist/                 # generated output (ignored by Git)
└── README.md
```

## Build

```bash
python3 scripts/build.py
```

The generator rebuilds `dist/` from scratch, copies assets, writes `sitemap.xml`, `robots.txt`, `_headers`, `assets/site.webmanifest`, and `404.html`. It then validates:

- internal links resolve to generated files;
- every page has `lang`, `<title>`, meta description, and one `<h1>`;
- no placeholder tokens or email-like strings leak into the output.

Expected tail:

```
Validated 17 HTML pages: links, lang, title, description, h1, no placeholders.
Built 17 pages into .../dist
```

## Preview

```bash
python3 -m http.server 8788 --directory dist
```

Open <http://127.0.0.1:8788/>. The 404 page is served as `/404.html` by this simple server; Cloudflare Pages serves it automatically for missing paths.

## Deploy

The Cloudflare Pages project is `lingxifox-apps` and uses **Direct Upload**. There is no Git-connected build.

### Automatic deployment

`.github/workflows/deploy.yml` runs on every push to `main` and on manual `workflow_dispatch`. It builds with `scripts/build.py`, verifies the BLAKE3 implementation, installs Node.js 22 and the official `cf` CLI, uploads changed assets through the Pages Direct Upload API, creates a production deployment on branch `main` with `cf pages deployments create`, waits for it to finish, and checks that both `https://lingxifox-apps.pages.dev/` and `https://apps.lingxifox.cn/` return the exact bytes of the new `dist/index.html`. A failed build, upload, deployment, or verification exits non-zero.

The workflow uses a repository secret named `CLOUDFLARE_API_TOKEN`:

1. In the Cloudflare dashboard, create a **custom API token** with account permission **Cloudflare Pages: Edit**. Reading Pages is sufficient to inspect, but deployment needs Edit.
2. Restrict it to the LingXiFox account if the dashboard offers that scope.
3. Store it without printing it:

```bash
gh secret set CLOUDFLARE_API_TOKEN -R LingXiFox/apps-site
```

Optionally store `CLOUDFLARE_ACCOUNT_ID` as a second secret; otherwise the workflow and scripts use `09c58146832fbea01ce12d3e316a1d4d`. The token is only read from the environment and is never written to the repository or printed by the scripts.

`cf pages deploy` does not implement legacy Pages Direct Upload. The official `cf pages deployments create` command does accept a Direct Upload manifest and the `_headers` file, so the workflow creates deployments with `cf` and uses `scripts/deploy_pages.py` for the upload-token exchange, missing-asset upload, polling, and byte verification. It does not use Wrangler.

### Local deployment

Requirements: Python 3.12, Node.js 22 or newer, and the official `cf` CLI (`npm install --global cf@1.0.0-beta.12`).

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=09c58146832fbea01ce12d3e316a1d4d
./scripts/deploy.sh
```

`scripts/deploy.sh` builds, runs the BLAKE3 self-test, deploys `dist/` to the production branch `main`, and verifies both hostnames. To deploy a prebuilt directory without rebuilding:

```bash
python3 scripts/deploy_pages.py --dist dist --project lingxifox-apps --branch main
```

The uploader prints only counts, deployment status, and verification digests. Assets already present in Pages are not uploaded again. HTTP 429 and 5xx responses are retried with backoff; a failed upload, deployment, or content check returns a non-zero exit status.

## Custom domain

The custom domain `apps.lingxifox.cn` is active and serves the Pages deployment. It currently resolves through a direct `CNAME` to `lingxifox-apps.pages.dev`. The DNS zone is managed outside this repository. Do not change the root nameservers, the existing records, or the ICP filing.

Verify the live path:

```bash
dig +short apps.lingxifox.cn CNAME
curl -I https://apps.lingxifox.cn/
```

Expected CNAME target: `lingxifox-apps.pages.dev.`. The domain is attached to the Pages project as a custom domain; Cloudflare issues and renews its certificate. Do not point the CNAME at an individual deployment hash such as `491c8199.lingxifox-apps.pages.dev`.

## Editing content

Edit the matching file under `content/`. Keep the same top-level keys across all four files: the generator reads `meta`, `nav`, `common`, `footer`, `home`, `texel`, `privacy`, `support`, and `notfound` from each language. The `prefix` value controls the URL prefix.

Product facts live in the same dictionaries, including the 5-photos-per-day free quota, 9-photo batch limit, supported formats, Pro one-time purchase, and App Store availability. Do not add screenshots, prices, review status, or legal details that are not true.

## Privacy

The site does not load analytics, advertising, fonts, or scripts from third parties. The privacy policy distinguishes on-device App processing from Cloudflare Pages request logs. Public support runs through GitHub Issues; no private email address is published.

## License

Site copy and brand assets are © 2026 LingXiFox. No license is granted for the LingXiFox name, the Texel name, or the app icon.
