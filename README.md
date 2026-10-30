# BreezeDelegate

I work on the problems that show up once software has to run somewhere. A deployment breaks, a service slows down, an API behaves differently than expected, or a server needs to survive something its original setup never anticipated. I like figuring out what went wrong and fixing the underlying problem.

Most of my work involves Linux, Python, Docker and backend systems. I also build web applications, automation tools and software around multiplayer games.

## Things I've worked on

- **Linux infrastructure:** VPS administration, containers, reverse proxies, backup and restore workflows, CI, monitoring and production troubleshooting.
- **Web platforms and automation:** publishing systems, operational dashboards, bots, API integrations and internal tools.
- **Game servers:** operating Minecraft and Rust environments, dealing with performance, configuration, plugins and service reliability.

Some of these systems are private or tied to specific projects, so their source code isn't here. The public projects and contributions below are easier to inspect.

## Current projects

### [BeforeUp](https://github.com/BreezeDelegate/beforeup)

<a href="https://github.com/BreezeDelegate/beforeup">
  <img src="https://raw.githubusercontent.com/BreezeDelegate/beforeup/main/assets/readme-banner.webp" alt="BeforeUp — Docker Compose preflight and deployment-change checks" width="620" />
</a>

A read-only Linux CLI for checking Docker Compose projects before deployment. It flags host port conflicts and missing bind-mount paths, and can compare planned changes with running containers.

### [Wisp MCP](https://github.com/BreezeDelegate/wisp-mcp)

A Python integration for MCP-compatible clients working with WISP game panels. It covers server resources, files, console commands, backups and databases, with permission controls for sensitive actions. The code is public under the PolyForm Noncommercial license.

## Upstream contributions

A few upstream changes I've contributed:

- [LinuxGSM](https://github.com/GameServerManagers/LinuxGSM/pull/4952): support for Debian's deb822 APT source files.
- [Neovide](https://github.com/neovide/neovide/pull/3552): hardening Neovim restart handling.
- [tailcat](https://github.com/tailscale/tailcat/pull/123): use SFTP when SCP supports it.

## Open source and collaboration

I'm interested in good ideas, especially when there's a difficult technical problem to untangle. I'm happy to review an approach, share a second opinion or contribute a fix to a project I find worthwhile, even when there's no paid work involved.

For infrastructure work, backend integrations or agency subcontracting, find me at **[vitrine.bar](https://vitrine.bar/)**.

<details>
<summary>GitHub activity</summary>

![GitHub activity](./github-metrics.svg)

</details>
