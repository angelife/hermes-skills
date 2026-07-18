# Claude Desktop 3P Managed MCP Schema Evidence

## Source
- App version: 1.18286.0
- Binary resource: `/Applications/Claude.app/Contents/Resources/ion-dist/assets/v1/c4b350ac1-BTR_0NaM.js`
- Also present in: `/Applications/Claude.app/Contents/Resources/ion-dist/assets/v1/c71860c77-CFD4jTV1.js`

## Key Findings

### Field name
- Managed config key: `managedMcpServers`
- NOT `mcpServers`
- Error when wrong: `Failed to parse managed config "managedMcpServers": .: invalid_type`

### Type
- Must be array of entries
- NOT object/map

### Entry shape
Each entry requires:
- `name`: string, server name
- `transport`: `stdio` or `http` or `sse`
- stdio transport needs: `command` + `args`
- http transport needs: `url` + optional `headers` / `oauth`

### Runtime behavior
- Desktop 3P mode uses `managedMcpServers` directly
- UI registry may not display managed entries
- Tool exposure can differ from service `tools/list` due to policy shaping
- Process command line contains `--managed-settings {"allowManagedMcpServersOnly":true,...}`

### Verification
- Log path: `~/Library/Logs/Claude-3p/main.log`
- Tool call evidence: `Emitted tool permission request for mcp__hindsight__<tool>`
- Success evidence: `Received permission response ... Turn succeeded`
