# LingXiFox Apps

Source for **https://apps.lingxifox.cn**, the LingXiFox software hub. The first product is **Texel (纹粒)**, a local HEIC texture tool for iPhone.

The site is a static, four-language marketing and support site. It has no client-side JavaScript, no backend, no database, no third-party analytics, and no tracking. All pages are generated from Python content dictionaries and plain HTML/CSS.

## Live

- Production domain: <https://apps.lingxifox.cn/> (custom domain attached; DNS verification is pending)
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
├── scripts/
│   ├── build.py          # static generator + link/content validation
│   └── deploy.sh         # build, then deploy to Cloudflare Pages
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

```bash
export CLOUDFLARE_ACCOUNT_ID=09c58146832fbea01ce12d3e316a1d4d
npx wrangler login
./scripts/deploy.sh
```

Or use a scoped API token instead of an interactive login:

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=09c58146832fbea01ce12d3e316a1d4d
./scripts/deploy.sh
```

The script builds, checks that Wrangler is authenticated when no token is supplied, and deploys `dist/` to the production branch `main`. The one-line equivalent is:

```bash
npx wrangler pages deploy dist --project-name lingxifox-apps --branch main --commit-dirty=true
```

A GitHub Actions deployment is intentionally not checked in: the repository has no durable Cloudflare API token configured, and an OAuth session must not be stored as a GitHub secret. Add a scoped `Pages:Edit` token as `CLOUDFLARE_API_TOKEN` plus `CLOUDFLARE_ACCOUNT_ID` if automatic deployment is required later.

## Custom domain

The custom domain `apps.lingxifox.cn` is attached to the Pages project. DNS is managed at Aliyun; do not change the root nameservers, existing records, or ICP filing.

Create this record in the Aliyun DNS console:

| Type | Host | Value | TTL |
| --- | --- | --- | --- |
| CNAME | `apps` | `lingxifox-apps.pages.dev` | Auto (or 600 s) |

Cloudflare shows the domain as `pending` with `CNAME record not set` until that record resolves. Certificate issuance starts automatically after validation. Do not point the CNAME at an individual deployment hash such as `e3a07936.lingxifox-apps.pages.dev`.

## Editing content

Edit the matching file under `content/`. Keep the same top-level keys across all four files: the generator reads `meta`, `nav`, `common`, `footer`, `home`, `texel`, `privacy`, `support`, and `notfound` from each language. The `prefix` value controls the URL prefix.

Product facts live in the same dictionaries, including the 5-photos-per-day free quota, 9-photo batch limit, supported formats, Pro one-time purchase, and App Store availability. Do not add screenshots, prices, review status, or legal details that are not true.

## Privacy

The site does not load analytics, advertising, fonts, or scripts from third parties. The privacy policy distinguishes on-device App processing from Cloudflare Pages request logs. Public support runs through GitHub Issues; no private email address is published.

## License

Site copy and brand assets are © 2026 LingXiFox. No license is granted for the LingXiFox name, the Texel name, or the app icon.
