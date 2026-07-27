---
name: jfrog-search-docker-image
description: Find available Docker image tags in JFrog Artifactory using the `jf` CLI, especially when a user asks to search Artifactory/JFrog for a Python, base, CI, Docker, or container image tag and choose a concrete repository image string.
---

# JFrog Docker Image Search

Use this skill to verify image tags that actually exist in Artifactory before editing CI/CD image references.

## Workflow

1. Confirm `jf` is installed and configured:

   ```bash
   jf --version
   jf c show
   ```

2. Prefer the Docker registry tag API over raw artifact glob searches. Docker repositories may not expose tag directories in a way that `jf rt s` can find reliably.

3. In Codex sandboxed sessions, Artifactory hostnames commonly fail DNS resolution until the command is rerun with escalated network access. If any `jf` command fails with `lookup <host>: no such host`, rerun the same JFrog query or helper command immediately with network escalation instead of retrying inside the sandbox.

4. For exact or narrow tag checks, prefer the bundled helper first so output stays small and unambiguous:

   ```bash
   python ~/.codex/skills/jfrog-search-docker-image/scripts/filter_docker_tags.py \
     --repo public-docker-prod \
     --image library/python \
     --prefix 3.12 \
     --contains slim
   ```

5. List raw tags with `jf rt curl` when the helper is not enough or broader inspection is needed:

   ```bash
   jf rt curl "/api/docker/<repo>/v2/<image-path>/tags/list"
   ```

   Example for Python official images mirrored in Artifactory:

   ```bash
   jf rt curl "/api/docker/public-docker-prod/v2/library/python/tags/list"
   ```

6. Report the exact usable image string:

   ```text
   <registry-host>/<repo>/<image-path>:<tag>
   ```

## Notes

- If `jf` fails with DNS or network errors in Codex, rerun the JFrog query/helper with escalated network access and continue from that result. Do not repeat non-network setup checks such as `jf --version` or `jf c show`.
- If a broad tag-list response is large, use the helper script so only matching tags are shown.
- Use `library/python` for official Python images in `public-docker-prod`; `python` alone may return `NAME_UNKNOWN`.
- If a manifest check fails for a tag that appears in `tags/list`, trust `tags/list` for availability unless the user specifically asks to debug the manifest API path or headers.
