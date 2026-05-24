<h3 align="center">
    <img src="https://i.ibb.co/CWY693F/beatprints-logo.png" width="175"/>
</h3>
<h3 align="center">
    BeatPrints Open: Quick, stylish posters for your favorite tracks!
</h3>

<p align="center">Create eye-catching, Pinterest-style music posters without Spotify Premium. This fork uses Apple iTunes Search first, Deezer as a fallback, and LRCLIB for lyrics.</p>

> This is a non-commercial derivative of [TrueMyst/BeatPrints](https://github.com/TrueMyst/BeatPrints). It remains licensed under CC BY-NC-SA 4.0. Major changes include replacing Spotify Premium-dependent metadata lookup with open metadata providers and rendering link QR codes instead of Spotify scannables.

<p align="center">
  <a href="https://gitHub.com/TrueMyst/BeatPrints/graphs/commit-activity">
    <img alt="Maintenance" src="https://img.shields.io/badge/Maintained%3F-Yes-%23c4b9a6?style=for-the-badge&logo=Undertale&logoColor=%23b5a790&labelColor=%23312123"></a>

  <a href="https://github.com/TrueMyst/BeatPrints/stargazers">
    <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/TrueMyst/BeatPrints?style=for-the-badge&logo=Apache%20Spark&logoColor=%23b5a790&labelColor=%23312123&color=%23c4b9a6"></a>

  <a href="https://pepy.tech/projects/BeatPrints">
    <img alt="Downloads" src="https://img.shields.io/pepy/dt/BeatPrints?style=for-the-badge&logo=pypi&logoColor=%23C4B9A6&labelColor=%23312123&color=%23C4B9A6"></a>

  <a href="https://github.com/psf/black">
    <img alt="Code Formatter" src="https://img.shields.io/badge/Code_Style-black-%23c4b9a6?style=for-the-badge&logo=CodeFactor&logoColor=%23b5a790&labelColor=%23312123"></a>

  <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">
    <img alt="Static Badge" src="https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-%23c4b9a6?style=for-the-badge&logo=Pinboard&logoColor=%23b5a790&labelColor=%23312123"></a>
</p>


![examples](https://i.imgur.com/tQdIeIU.png)

<h3 align="center">📔 Check out the documentation <a href="https://beatprints.readthedocs.io/en/latest/">here!</a></h3>

## 📦 Installation

You can install this fork from a local checkout:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 🚀 Quick Start

### 🌱 Environment Variables

No Spotify credentials are required for track or album lookup in this fork.

### 🎀 Creating your FIRST Poster
Here’s how you can create your first poster:

```python
from BeatPrints import lyrics, poster, spotify

# Initialize components
ly = lyrics.Lyrics()
ps = poster.Poster("./")
sp = spotify.Spotify()

# Search for the track and fetch metadata
search = sp.get_track("Saturn - SZA", limit=1)

# Pick the first result
metadata = search[0]

# Get lyrics and determine if the track is instrumental
lyrics = ly.get_lyrics(metadata)

# Use the placeholder for instrumental tracks; otherwise, select specific lines
highlighted_lyrics = (
    lyrics if ly.check_instrumental(metadata) else ly.select_lines(lyrics, "5-9")
)

# Generate the track poster
ps.track(metadata, highlighted_lyrics)
```

## 🥞 CLI

Here’s a short video showing how to generate posters using the CLI. For more information refer to the documentation [here](https://beatprints.readthedocs.io/en/latest/guidebook/cli.html)

https://github.com/user-attachments/assets/3efb7028-c533-4bf4-880b-da3a71f8a3db

## 🖥️ Local Web UI

This fork also includes a local browser interface:

```bash
source .venv/bin/activate
beatprints-web
```

Then open:

```text
http://127.0.0.1:8010
```

The web UI supports track search, result selection, LRCLIB lyrics lookup with a lyrics.ovh fallback, full manual track entry, manual lyrics entry, theme selection, accent color, poster generation, preview, and download.

Use the **Manual** tab for unreleased songs or songs that are not available in
Apple's catalog. Manual mode accepts track name, artist, album, release date,
duration, label, cover image URL, playback link, and lyrics. The playback link is
used for the poster's QR/scannable area, so it can point to any platform.

Generated posters are returned directly from `/api/generate` as `image/png`. The browser previews the response with a temporary blob URL and uses that same blob for download. This avoids depending on a persistent server `output/` directory and is the preferred contract for serverless deployments such as Vercel.

## ☁️ Deploy

BeatPrints Open is a dynamic Python web service. It must run as a web service or
container, not as a static site.

### Vercel

This repository includes a Vercel-compatible serverless layout:

- `public/` contains the static web UI.
- `api/search.py`, `api/lyrics.py`, and `api/generate.py` are Python Vercel Functions.
- `api/generate.py` returns `image/png` directly instead of writing to `output/`.
- Image generation uses `/tmp` only as short-lived scratch space.

Deploy from GitHub by importing the repository into Vercel. Vercel will install
dependencies from `requirements.txt` and use `vercel.json` for function settings.

Direct image responses are the lowest-cost option because no generated posters are
stored after the request. Refreshing the page loses the temporary preview URL, so
the user must regenerate the poster if they need it again.

### Future image storage options

If generated posters need permanent URLs, history, or share links, add object
storage after generation:

- Vercel Blob: easiest on Vercel. Hobby includes limited free usage; Pro can pay
  for additional usage. Best when staying inside the Vercel platform.
- Cloudflare R2: best low-cost generic image storage. It has a larger free tier
  than Vercel Blob for storage and operations, and direct R2 egress is free. Best
  choice for a simple poster image bucket.
- Cloudinary: best if you want a media dashboard, search, CDN delivery, and image
  transformation features. Its free plan uses monthly credits across storage,
  bandwidth, and transformations, so it is more feature-rich but less direct than R2.

Recommended upgrade path:

1. Start with direct `image/png` responses.
2. Add Cloudflare R2 when posters need permanent shareable URLs.
3. Consider Cloudinary only if media management and transformations become useful.

### Custom domain and access protection

You can attach a Cloudflare-managed domain to the Vercel deployment:

1. Add the domain in Vercel project settings under Domains.
2. In Cloudflare DNS, point a subdomain such as `beatprints.example.com` to
   `cname.vercel-dns.com` with a CNAME record.
3. Keep the Cloudflare proxy disabled until Vercel finishes domain verification
   and certificate provisioning. Re-enable proxy only after verifying the domain
   works correctly.

For login protection, the recommended options are:

- Cloudflare Access: best for keeping the public app private behind an email,
  identity provider, one-time PIN, or service policy. This works well when the
  domain is managed by Cloudflare.
- Vercel Deployment Protection: built into Vercel, but production password
  protection depends on the account/team plan.
- App-level username/password: possible, but this static + Python Functions
  layout would need to route every page and API request through an auth layer.
  Cloudflare Access is cleaner for this project.

### Render

This repository includes `render.yaml` and `Dockerfile`.

1. Push this repository to GitHub.
2. In Render, create a new Blueprint or Web Service from the repository.
3. Use the Docker runtime.
4. Deploy.

The service starts with:

```bash
python -m web.app --host 0.0.0.0
```

### Fly.io

Copy `fly.toml.example` to `fly.toml`, change the app name, then run:

```bash
fly launch --no-deploy
fly deploy
```

Generated posters are returned directly by the API. For a public service, add
rate limiting. If users need persistent poster URLs, upload generated PNG files
to object storage such as Cloudflare R2, Vercel Blob, or Cloudinary.

## 🖼️ Examples

| **Track: Saturn by SZA**                                             | **Album: Charm by Clairo**                                             |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| ![Track Example](https://i.imgur.com/wWUbdK1.png)                    | ![Album Example](https://i.imgur.com/9vlD94t.png)                      |


## 🎨 Themes
BeatPrints currently offers you **5 additional themes**  to use! 
- Catppuccin
- Gruvbox
- Nord
- Rosepine
- Everforest

For original examples, check out the [upstream examples directory](https://github.com/TrueMyst/BeatPrints/tree/main/examples).


## ✨ Features

- **Polaroid Filter for Covers**: Give your track or album covers a vintage Polaroid look.  
- **Multi-language Support**: Supports English, Hindi, Russian, Japanese, Chinese, and Korean.  
- **Custom Cover Images**: Personalize posters with your own images.  
- **Theme Customization**: Switch between different other themes.
- **Track & Album Selection**: Highlight your favorite track or entire album.  
- **Lyrics Highlighting**: Highlight your favourite lyrics directly on your poster.
- **No Spotify Premium Required**: Track metadata comes from Apple iTunes Search with Deezer fallback.


## 🤝 Contributors

Thank you to all contributors for making BeatPrints better!

<p align="center">
 <a href="https://github.com/TrueMyst/BeatPrints/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=TrueMyst/BeatPrints" />
 </a>
</p>


## 💡 Why BeatPrints?

I created this project after finding out that people sell these posters on [Etsy](https://www.etsy.com/market/spotify_poster) at high prices, offering only digital downloads instead of shipping actual posters. 

I wanted to make it free for everyone to print themselves, as I believe my posters are simpler, cleaner, and prettier.


## ❤️  Special Thanks

- A big thanks to [Spotify Poster Generator](https://github.com/AnveshakR/poster-generator/) by [@AnveshakR](https://github.com/AnveshakR) for inspiring BeatPrints with amazing ideas!  
- Shoutout to [@Magniquick](https://github.com/Magniquick), [@itsnotrin](https://github.com/itsnotrin), [@wenbang24](https://github.com/wenbang24) and [@cherriae](https://github.com/cherriae) for their awesome contributions!


## 📜 License

BeatPrints is distributed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**:

- **Use**: Free to share and adapt.  
- **Attribution**: Provide credit and a link to the license.  
- **NonCommercial**: Not for commercial use.  
- **ShareAlike**: Adaptations must follow the same license.  

Read the full license [here](https://github.com/TrueMyst/BeatPrints/blob/main/LICENSE).  


<p align="center">
Made with 💜 <br>
elysianmyst, 2025
</p>
