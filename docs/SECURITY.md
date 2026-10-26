# Trust and safety model

- Prompt injection and generated specifications are untrusted; engine parameters enforced server-side.
- Executable templates maintained and reviewed by maintainers. No arbitrary model-generated executable scripts.
- Worker containers: unprivileged, isolated, no host mounts, egress restricted, memory/cpu/time limits.
- Validate uploads and scientific artifacts, prohibit path traversal and symlink escapes.
- Authentication and per-workspace access controls before enabling persisted/shared experiments.
- Audit run initiator, engine binary, input digest, resource usage and artifact access.
- Deny unsupported/unsafe execution requests, explain alternate valid models.
- Product for research/education, not clinical decisions. Clearly distinguish hypothesis generation from validated science.
