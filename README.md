# seerr-mcp

Part of the [arr-mcps](https://github.com/SavageCore/arr-mcps) collection.
MCP server exposing [Seerr](https://github.com/seerr-team/seerr)'s v1 REST API
([OpenAPI 3.0.2](https://seerr-team.github.io/)) as tools, so an LLM can read
and manage a Seerr instance: search and discovery, media requests and their
approval workflow, users, issues, watchlists and blocklists, Plex/Jellyfin/Emby
and Sonarr/Radarr integration settings, notification agents, scheduled jobs,
and more. Full surface — reads **and** writes, with destructive tools flagged.

Built with [FastMCP](https://gofastmcp.com).

## Getting an API key

Generate one in Seerr **Settings > General**. Auth is the `X-Api-Key` header.
An optional `X-API-User` header can impersonate a specific user id (defaults
to user 1, the admin account the key belongs to).

## Install

Download a wheel from the [latest release](https://github.com/SavageCore/seerr-mcp/releases/latest)
and install it as a `uv` tool (no repo checkout needed):

```bash
uv tool install seerr_mcp-*.whl
```

This puts a `seerr-mcp` command on your PATH. Register it with Claude Code:

```bash
claude mcp add seerr \
  --env SEERR_URL=http://your-seerr-host \
  --env SEERR_API_KEY=<key> \
  -- seerr-mcp
```

### From source

```bash
uv sync
cp .env.example .env   # fill in SEERR_URL and SEERR_API_KEY
```

```bash
claude mcp add seerr \
  --env SEERR_URL=http://your-seerr-host \
  --env SEERR_API_KEY=<key> \
  -- uv run --directory /path/to/seerr-mcp seerr-mcp
```

## Config

| Env var | Required | Default |
|---|---|---|
| `SEERR_URL` | yes | - |
| `SEERR_API_KEY` | yes* | none (no `X-Api-Key` header sent if unset) |
| `SEERR_API_USER` | no | none (no `X-API-User` header; API key acts as user 1) |

\* Every API endpoint requires auth; practically you must set it, but the
server still starts without one so errors surface from the API rather than at
startup.

## Tools

One tool per Seerr v1 JSON endpoint (208 tools). Naming is
`seerr_<verb>_<resource>`. GET endpoints are read-only; POST/PUT are writes;
DELETE endpoints are flagged destructive. One exception: `GET
/settings/discover/reset` resets all discover sliders and is therefore marked
a write.

Endpoints are grouped below by the spec's tags. Request bodies are passed as
opaque JSON objects/lists (`body` argument); see the vendored spec at
`tests/data/seerr_openapi.yml` for the exact fields each accepts.

| Tool | Method | Endpoint |
|---|---|---|
| **Public** | | |
| `seerr_list_status` | GET | `/status` |
| `seerr_list_status_appdata` | GET | `/status/appdata` |
| **Settings** | | |
| `seerr_list_settings_main` | GET | `/settings/main` |
| `seerr_create_settings_main` | POST | `/settings/main` |
| `seerr_list_settings_network` | GET | `/settings/network` |
| `seerr_create_settings_network` | POST | `/settings/network` |
| `seerr_regenerate_api_key` | POST | `/settings/main/regenerate` |
| `seerr_list_settings_jellyfin` | GET | `/settings/jellyfin` |
| `seerr_create_settings_jellyfin` | POST | `/settings/jellyfin` |
| `seerr_list_settings_jellyfin_library` | GET | `/settings/jellyfin/library` |
| `seerr_list_settings_jellyfin_users` | GET | `/settings/jellyfin/users` |
| `seerr_list_settings_jellyfin_sync` | GET | `/settings/jellyfin/sync` |
| `seerr_create_settings_jellyfin_sync` | POST | `/settings/jellyfin/sync` |
| `seerr_list_settings_plex` | GET | `/settings/plex` |
| `seerr_create_settings_plex` | POST | `/settings/plex` |
| `seerr_list_settings_plex_library` | GET | `/settings/plex/library` |
| `seerr_list_settings_plex_sync` | GET | `/settings/plex/sync` |
| `seerr_create_settings_plex_sync` | POST | `/settings/plex/sync` |
| `seerr_list_settings_plex_devices_servers` | GET | `/settings/plex/devices/servers` |
| `seerr_list_settings_plex_users` | GET | `/settings/plex/users` |
| `seerr_list_settings_metadatas` | GET | `/settings/metadatas` |
| `seerr_update_settings_metadatas` | PUT | `/settings/metadatas` |
| `seerr_create_settings_metadatas_test` | POST | `/settings/metadatas/test` |
| `seerr_list_settings_tautulli` | GET | `/settings/tautulli` |
| `seerr_create_settings_tautulli` | POST | `/settings/tautulli` |
| `seerr_list_settings_radarr` | GET | `/settings/radarr` |
| `seerr_create_settings_radarr` | POST | `/settings/radarr` |
| `seerr_create_settings_radarr_test` | POST | `/settings/radarr/test` |
| `seerr_update_settings_radarr` | PUT | `/settings/radarr/{radarrId}` |
| `seerr_delete_settings_radarr` | DELETE | `/settings/radarr/{radarrId}` |
| `seerr_get_settings_radarr_profiles` | GET | `/settings/radarr/{radarrId}/profiles` |
| `seerr_list_settings_sonarr` | GET | `/settings/sonarr` |
| `seerr_create_settings_sonarr` | POST | `/settings/sonarr` |
| `seerr_create_settings_sonarr_test` | POST | `/settings/sonarr/test` |
| `seerr_update_settings_sonarr` | PUT | `/settings/sonarr/{sonarrId}` |
| `seerr_delete_settings_sonarr` | DELETE | `/settings/sonarr/{sonarrId}` |
| `seerr_list_settings_public` | GET | `/settings/public` |
| `seerr_initialize_app` | POST | `/settings/initialize` |
| `seerr_list_settings_jobs` | GET | `/settings/jobs` |
| `seerr_run_job` | POST | `/settings/jobs/{jobId}/run` |
| `seerr_cancel_job` | POST | `/settings/jobs/{jobId}/cancel` |
| `seerr_schedule_job` | POST | `/settings/jobs/{jobId}/schedule` |
| `seerr_list_settings_cache` | GET | `/settings/cache` |
| `seerr_flush_cache` | POST | `/settings/cache/{cacheId}/flush` |
| `seerr_flush_dns_cache` | POST | `/settings/cache/dns/{dnsEntry}/flush` |
| `seerr_list_settings_logs` | GET | `/settings/logs` |
| `seerr_list_settings_notifications_email` | GET | `/settings/notifications/email` |
| `seerr_create_settings_notifications_email` | POST | `/settings/notifications/email` |
| `seerr_create_settings_notifications_email_test` | POST | `/settings/notifications/email/test` |
| `seerr_list_settings_notifications_discord` | GET | `/settings/notifications/discord` |
| `seerr_create_settings_notifications_discord` | POST | `/settings/notifications/discord` |
| `seerr_create_settings_notifications_discord_test` | POST | `/settings/notifications/discord/test` |
| `seerr_list_settings_notifications_pushbullet` | GET | `/settings/notifications/pushbullet` |
| `seerr_create_settings_notifications_pushbullet` | POST | `/settings/notifications/pushbullet` |
| `seerr_create_settings_notifications_pushbullet_test` | POST | `/settings/notifications/pushbullet/test` |
| `seerr_list_settings_notifications_pushover` | GET | `/settings/notifications/pushover` |
| `seerr_create_settings_notifications_pushover` | POST | `/settings/notifications/pushover` |
| `seerr_create_settings_notifications_pushover_test` | POST | `/settings/notifications/pushover/test` |
| `seerr_list_pushover_sounds` | GET | `/settings/notifications/pushover/sounds` |
| `seerr_list_settings_notifications_gotify` | GET | `/settings/notifications/gotify` |
| `seerr_create_settings_notifications_gotify` | POST | `/settings/notifications/gotify` |
| `seerr_create_settings_notifications_gotify_test` | POST | `/settings/notifications/gotify/test` |
| `seerr_list_settings_notifications_ntfy` | GET | `/settings/notifications/ntfy` |
| `seerr_create_settings_notifications_ntfy` | POST | `/settings/notifications/ntfy` |
| `seerr_create_settings_notifications_ntfy_test` | POST | `/settings/notifications/ntfy/test` |
| `seerr_list_settings_notifications_slack` | GET | `/settings/notifications/slack` |
| `seerr_create_settings_notifications_slack` | POST | `/settings/notifications/slack` |
| `seerr_create_settings_notifications_slack_test` | POST | `/settings/notifications/slack/test` |
| `seerr_list_settings_notifications_telegram` | GET | `/settings/notifications/telegram` |
| `seerr_create_settings_notifications_telegram` | POST | `/settings/notifications/telegram` |
| `seerr_create_settings_notifications_telegram_test` | POST | `/settings/notifications/telegram/test` |
| `seerr_list_settings_notifications_webpush` | GET | `/settings/notifications/webpush` |
| `seerr_create_settings_notifications_webpush` | POST | `/settings/notifications/webpush` |
| `seerr_create_settings_notifications_webpush_test` | POST | `/settings/notifications/webpush/test` |
| `seerr_list_settings_notifications_webhook` | GET | `/settings/notifications/webhook` |
| `seerr_create_settings_notifications_webhook` | POST | `/settings/notifications/webhook` |
| `seerr_create_settings_notifications_webhook_test` | POST | `/settings/notifications/webhook/test` |
| `seerr_list_discover_sliders` | GET | `/settings/discover` |
| `seerr_update_discover_sliders` | POST | `/settings/discover` |
| `seerr_update_discover_slider` | PUT | `/settings/discover/{sliderId}` |
| `seerr_delete_discover_slider` | DELETE | `/settings/discover/{sliderId}` |
| `seerr_add_discover_slider` | POST | `/settings/discover/add` |
| `seerr_reset_discover_sliders` | GET* | `/settings/discover/reset` |
| `seerr_list_settings_about` | GET | `/settings/about` |
| **Auth** | | |
| `seerr_get_me` | GET | `/auth/me` |
| `seerr_login_plex` | POST | `/auth/plex` |
| `seerr_login_jellyfin` | POST | `/auth/jellyfin` |
| `seerr_initiate_jellyfin_quickconnect` | POST | `/auth/jellyfin/quickconnect/initiate` |
| `seerr_check_jellyfin_quickconnect` | GET | `/auth/jellyfin/quickconnect/check` |
| `seerr_authenticate_jellyfin_quickconnect` | POST | `/auth/jellyfin/quickconnect/authenticate` |
| `seerr_login_local` | POST | `/auth/local` |
| `seerr_logout` | POST | `/auth/logout` |
| `seerr_request_password_reset` | POST | `/auth/reset-password` |
| `seerr_reset_password` | POST | `/auth/reset-password/{guid}` |
| **Users** | | |
| `seerr_list_user` | GET | `/user` |
| `seerr_create_user` | POST | `/user` |
| `seerr_batch_update_users` | PUT | `/user` |
| `seerr_import_plex_users` | POST | `/user/import-from-plex` |
| `seerr_import_jellyfin_users` | POST | `/user/import-from-jellyfin` |
| `seerr_register_push_subscription` | POST | `/user/registerPushSubscription` |
| `seerr_list_user_push_subscriptions` | GET | `/user/{userId}/pushSubscriptions` |
| `seerr_get_user_push_subscription` | GET | `/user/{userId}/pushSubscription/{endpoint}` |
| `seerr_delete_user_push_subscription` | DELETE | `/user/{userId}/pushSubscription/{endpoint}` |
| `seerr_get_user` | GET | `/user/{userId}` |
| `seerr_update_user` | PUT | `/user/{userId}` |
| `seerr_delete_user` | DELETE | `/user/{userId}` |
| `seerr_get_user_jellyfin` | GET | `/user/jellyfin/{jellyfinUserId}` |
| `seerr_get_user_requests` | GET | `/user/{userId}/requests` |
| `seerr_get_user_quota` | GET | `/user/{userId}/quota` |
| `seerr_get_user_watchlist` | GET | `/user/{userId}/watchlist` |
| `seerr_get_user_settings_main` | GET | `/user/{userId}/settings/main` |
| `seerr_create_user_settings_main` | POST | `/user/{userId}/settings/main` |
| `seerr_get_user_settings_password` | GET | `/user/{userId}/settings/password` |
| `seerr_create_user_settings_password` | POST | `/user/{userId}/settings/password` |
| `seerr_create_user_settings_linked_accounts_plex` | POST | `/user/{userId}/settings/linked-accounts/plex` |
| `seerr_delete_user_settings_linked_accounts_plex` | DELETE | `/user/{userId}/settings/linked-accounts/plex` |
| `seerr_create_user_settings_linked_accounts_jellyfin` | POST | `/user/{userId}/settings/linked-accounts/jellyfin` |
| `seerr_delete_user_settings_linked_accounts_jellyfin` | DELETE | `/user/{userId}/settings/linked-accounts/jellyfin` |
| `seerr_create_user_settings_linked_accounts_jellyfin_quickconnect` | POST | `/user/{userId}/settings/linked-accounts/jellyfin/quickconnect` |
| `seerr_get_user_settings_notifications` | GET | `/user/{userId}/settings/notifications` |
| `seerr_create_user_settings_notifications` | POST | `/user/{userId}/settings/notifications` |
| `seerr_get_user_settings_permissions` | GET | `/user/{userId}/settings/permissions` |
| `seerr_create_user_settings_permissions` | POST | `/user/{userId}/settings/permissions` |
| `seerr_get_user_watch_data` | GET | `/user/{userId}/watch_data` |
| **Search / Discover** | | |
| `seerr_list_search` | GET | `/search` |
| `seerr_list_search_keyword` | GET | `/search/keyword` |
| `seerr_list_search_company` | GET | `/search/company` |
| `seerr_list_discover_movies` | GET | `/discover/movies` |
| `seerr_get_discover_movies_genre` | GET | `/discover/movies/genre/{genreId}` |
| `seerr_get_discover_movies_language` | GET | `/discover/movies/language/{language}` |
| `seerr_get_discover_movies_studio` | GET | `/discover/movies/studio/{studioId}` |
| `seerr_list_discover_movies_upcoming` | GET | `/discover/movies/upcoming` |
| `seerr_list_discover_tv` | GET | `/discover/tv` |
| `seerr_get_discover_tv_language` | GET | `/discover/tv/language/{language}` |
| `seerr_get_discover_tv_genre` | GET | `/discover/tv/genre/{genreId}` |
| `seerr_get_discover_tv_network` | GET | `/discover/tv/network/{networkId}` |
| `seerr_list_discover_tv_upcoming` | GET | `/discover/tv/upcoming` |
| `seerr_list_discover_trending` | GET | `/discover/trending` |
| `seerr_get_discover_keyword_movies` | GET | `/discover/keyword/{keywordId}/movies` |
| `seerr_list_discover_genreslider_movie` | GET | `/discover/genreslider/movie` |
| `seerr_list_discover_genreslider_tv` | GET | `/discover/genreslider/tv` |
| `seerr_list_discover_watchlist` | GET | `/discover/watchlist` |
| **Requests** | | |
| `seerr_list_request` | GET | `/request` |
| `seerr_create_request` | POST | `/request` |
| `seerr_list_request_count` | GET | `/request/count` |
| `seerr_get_request` | GET | `/request/{requestId}` |
| `seerr_update_request` | PUT | `/request/{requestId}` |
| `seerr_delete_request` | DELETE | `/request/{requestId}` |
| `seerr_retry_request` | POST | `/request/{requestId}/retry` |
| `seerr_set_request_status` | POST | `/request/{requestId}/{status}` |
| **Movies** | | |
| `seerr_get_movie` | GET | `/movie/{movieId}` |
| `seerr_get_movie_recommendations` | GET | `/movie/{movieId}/recommendations` |
| `seerr_get_movie_similar` | GET | `/movie/{movieId}/similar` |
| `seerr_get_movie_ratings` | GET | `/movie/{movieId}/ratings` |
| `seerr_get_movie_ratingscombined` | GET | `/movie/{movieId}/ratingscombined` |
| **TV** | | |
| `seerr_get_tv` | GET | `/tv/{tvId}` |
| `seerr_get_tv_season` | GET | `/tv/{tvId}/season/{seasonNumber}` |
| `seerr_get_tv_recommendations` | GET | `/tv/{tvId}/recommendations` |
| `seerr_get_tv_similar` | GET | `/tv/{tvId}/similar` |
| `seerr_get_tv_ratings` | GET | `/tv/{tvId}/ratings` |
| **Media** | | |
| `seerr_list_media` | GET | `/media` |
| `seerr_delete_media` | DELETE | `/media/{mediaId}` |
| `seerr_delete_media_file` | DELETE | `/media/{mediaId}/file` |
| `seerr_set_media_status` | POST | `/media/{mediaId}/{status}` |
| `seerr_get_media_watch_data` | GET | `/media/{mediaId}/watch_data` |
| **People** | | |
| `seerr_get_person` | GET | `/person/{personId}` |
| `seerr_get_person_combined_credits` | GET | `/person/{personId}/combined_credits` |
| **Collections** | | |
| `seerr_get_collection` | GET | `/collection/{collectionId}` |
| **Services** | | |
| `seerr_list_service_radarr` | GET | `/service/radarr` |
| `seerr_get_service_radarr` | GET | `/service/radarr/{radarrId}` |
| `seerr_list_service_sonarr` | GET | `/service/sonarr` |
| `seerr_get_service_sonarr` | GET | `/service/sonarr/{sonarrId}` |
| `seerr_get_service_sonarr_lookup` | GET | `/service/sonarr/lookup/{tmdbId}` |
| **Watchlist** | | |
| `seerr_create_watchlist` | POST | `/watchlist` |
| `seerr_delete_watchlist` | DELETE | `/watchlist/{tmdbId}` |
| **Blocklist** | | |
| `seerr_list_blocklist` | GET | `/blocklist` |
| `seerr_create_blocklist` | POST | `/blocklist` |
| `seerr_get_blocklist` | GET | `/blocklist/{tmdbId}` |
| `seerr_delete_blocklist` | DELETE | `/blocklist/{tmdbId}` |
| `seerr_create_blocklist_collection` | POST | `/blocklist/collection/{collectionId}` |
| `seerr_delete_blocklist_collection` | DELETE | `/blocklist/collection/{collectionId}` |
| **TMDB helpers** | | |
| `seerr_list_regions` | GET | `/regions` |
| `seerr_list_languages` | GET | `/languages` |
| `seerr_get_studio` | GET | `/studio/{studioId}` |
| `seerr_get_network` | GET | `/network/{networkId}` |
| `seerr_list_genres_movie` | GET | `/genres/movie` |
| `seerr_list_genres_tv` | GET | `/genres/tv` |
| `seerr_list_backdrops` | GET | `/backdrops` |
| **Issues** | | |
| `seerr_list_issue` | GET | `/issue` |
| `seerr_create_issue` | POST | `/issue` |
| `seerr_list_issue_count` | GET | `/issue/count` |
| `seerr_get_issue` | GET | `/issue/{issueId}` |
| `seerr_delete_issue` | DELETE | `/issue/{issueId}` |
| `seerr_create_issue_comment` | POST | `/issue/{issueId}/comment` |
| `seerr_set_issue_status` | POST | `/issue/{issueId}/{status}` |
| **Issue comments** | | |
| `seerr_get_issuecomment` | GET | `/issueComment/{commentId}` |
| `seerr_update_issuecomment` | PUT | `/issueComment/{commentId}` |
| `seerr_delete_issuecomment` | DELETE | `/issueComment/{commentId}` |
| **Keywords** | | |
| `seerr_get_keyword` | GET | `/keyword/{keywordId}` |
| **Watch providers / certifications** | | |
| `seerr_list_watchproviders_regions` | GET | `/watchproviders/regions` |
| `seerr_list_watchproviders_movies` | GET | `/watchproviders/movies` |
| `seerr_list_watchproviders_tv` | GET | `/watchproviders/tv` |
| `seerr_list_certifications_movie` | GET | `/certifications/movie` |
| `seerr_list_certifications_tv` | GET | `/certifications/tv` |
| **Override rules** | | |
| `seerr_list_overriderule` | GET | `/overrideRule` |
| `seerr_create_overriderule` | POST | `/overrideRule` |
| `seerr_update_overriderule` | PUT | `/overrideRule/{ruleId}` |
| `seerr_delete_overriderule` | DELETE | `/overrideRule/{ruleId}` |

The deprecated `/blacklist/*` aliases (sunset 2026-06-01) are intentionally
not wrapped; use the `/blocklist/*` tools. Auth endpoints (`seerr_login_*`,
`seerr_logout`, `seerr_request_password_reset`) carry credentials or manage
sessions and are rarely needed through MCP when `SEERR_API_KEY` is already set.

## Development

```bash
make help  # list all commands
```

| Command | Does |
|---|---|
| `make sync` | `uv sync` |
| `make test` | Offline tests - one per endpoint, mocked HTTP |
| `make test-integration` | Tests against the live instance (needs `SEERR_URL`/`SEERR_API_KEY`) |
| `make build` | Build wheel + sdist into `dist/` |
| `make bump-patch` / `bump-minor` / `bump-major` | Bump the version in `pyproject.toml` + `uv.lock` |
| `make clean` | Remove build artifacts |

The release workflow (`.github/workflows/release.yml`) builds and publishes to
[Releases](https://github.com/SavageCore/seerr-mcp/releases) whenever a `v*`
tag is pushed - so the usual flow is `make bump-patch`, commit, then tag and
push.

The offline suite covers every endpoint (mocked HTTP). The integration suite
exercises GET endpoints against your live instance; POST/PUT/DELETE only run
when `SEERR_WRITE_TESTS=1`, as a safe create→delete cycle against a scratch
blocklist entry that is cleaned up afterwards.
