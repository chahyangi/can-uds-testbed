# Troubleshooting

- `gallia: command not found`: run `pipx ensurepath`, re-login, or use
  `$HOME/.local/bin/gallia`.
- Gallia 2.1.1 ISO-TP URI fields are `tx_id` and `rx_id`, not `src_addr` and
  `dst_addr`.
- `write: Invalid argument` from `isotpsend`: confirm that sender and receiver
  use opposite source/destination IDs and start the receiver first.
- Docker socket permission denied: use `sudo docker ...` for the lab, or add the
  user to the Docker group and re-login.
- SSH forwarding: this VM uses host `127.0.0.1:2022` to guest port 22. Verify
  the exact VirtualBox rule if a connection is refused.
- `Artifacts base folder not defined`: informational. The integration script
  captures stdout and CAN frames itself.
