# Releasing @unifuncs/ufn-mcp-server

This project documents both source builds and the npm `npx` installation path.

To keep the README accurate for `npx` users, release the npm package before describing newly added tools in the NPX section.

## Release Steps

1. Make sure the desired feature set is merged into `main`.
2. Bump `package.json` to the next release version.
3. Install dependencies.
4. Run `npm run build`.
5. Publish to npm.
6. Verify the published version:
   - `npm view @unifuncs/ufn-mcp-server version`
7. Smoke-test the published package:
   - `npx -y @unifuncs/ufn-mcp-server`
   - Run an MCP `tools/list` handshake and confirm the tool list matches the README.
8. Update the README and changelog if needed.

## Why This Matters

The source repository can move ahead of the latest npm release. If the README is updated before npm is published, `npx` users will get a package that does not match the documented feature set.
