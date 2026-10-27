# SSH source restriction: safety-first runbook

> **Non-executable guidance only.** Omarchy SSH Guard v0.1 does **not** apply firewall rules or finalize deployments.

## 1. Inventory and scope

Record the SSH server's actual listening port, host identity, intended clients, recovery endpoints, IPv4 and IPv6 paths, DNS dependencies and whether Docker modifies packet filtering. Ensure the workstation's keyboard/display login and sudo access work independently of SSH. Review UFW `status verbose` and `status numbered` from a trusted administrator session.

A rate-limited `Anywhere` SSH rule is not an allowlist. A source-specific rule does not override a simultaneous broad allowance. Default-deny inbound traffic is helpful but does not establish application safety or Docker forwarded-port isolation.

## 2. Confirm authentication and recovery

Compare the server's host-key fingerprint over a trustworthy out-of-band route. Test **a fresh, non-multiplexed** SSH public-key login from every authorized source. Verify effective OpenSSH authentication policy, including password, keyboard-interactive and remote root login separately. Do not downgrade host-key checks or enable passwords to make a test pass.

## 3. Preregister external negative tests

Before firewall deployment, independently controlled unauthorized IPv4 and IPv6 clients should prove that TCP/22 on the target is reachable on each applicable path. Record client ownership, source and destination addresses, paths, UTC baseline timestamps, tested ports and results in a **local restricted file**. Without a pre-change baseline, later timeouts may be caused by routing rather than your firewall.

If global IPv6 connectivity does not exist, record the limitation; do not claim to have validated independent IPv6 rejection.

## 4. Back up and arm rollback

Make a root-owned, mode-0600 firewall backup and verify you can restore it. Install the exact tested rollback helper in a root-owned directory, not from a user-writable checkout. Arm a systemd timer before changing UFW. Exercise its recovery path independently. Keep an active console or out-of-band connection.

## 5. Apply only after explicit approval

Only a separately audited privileged executor should add authorized source rules and then remove the broad rules. Preserve Docker/NAT, DNS and other unrelated UFW entries. Do not issue `ufw reset` or flush iptables/nftables to implement source restrictions.

## 6. Verify on the new rules

Test fresh authorized SSH, compare server login journal events to the expected client and deployment time, and test independently controlled unauthorized IPv4/IPv6 connections. Require exact pre- and post-change target/path consistency. A timeout by itself is inconclusive.

## 7. Finalize or restore

Accept only genuine, timestamp-consistent evidence. The rollback timer stays armed until all required gates pass and the trusted executor atomically records the transaction as verified and cancels it. If the deadline expires or a check is missing, allow rollback; verify restored UFW state and fresh SSH access. Never fabricate evidence or manually disable the timer to preserve a potentially unverified configuration.

## Docker and additional services

Check published ports and host-network containers separately. Prefer `127.0.0.1:HOSTPORT:CONTAINERPORT` for genuinely host-only services, and do not rely on UFW `INPUT` rules to govern all Docker published traffic. Retest reachability from an independent machine. Never assume a localhost self-connect proves remote isolation.

See [Docker's firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/).
