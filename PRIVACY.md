## Privacy Policy

`whoop-mcp` stores WHOOP OAuth tokens locally on the user's machine so the MCP server can access the WHOOP API on the user's behalf.

The server is designed for local use. WHOOP data retrieved through the server is processed locally and is not intentionally transmitted to any third-party service by this project.

Data this project may store locally:

- WHOOP OAuth access tokens
- WHOOP OAuth refresh tokens
- MCP tool inputs and outputs handled by the local MCP client

Token storage is controlled by the local installation and defaults to a file on the user's machine. Users are responsible for securing their local environment and any downstream MCP client logs or transcripts.

This project does not provide a hosted backend, shared database, analytics service, or advertising.

Users can revoke access by revoking the WHOOP app authorization and deleting locally stored tokens.

For questions about this project, use the repository issue tracker.
