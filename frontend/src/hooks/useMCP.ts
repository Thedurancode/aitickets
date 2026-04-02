/**
 * useMCP Hook
 *
 * React hook for communicating with AI-Tickets MCP server.
 * Replace this with your actual MCP client implementation.
 */

import { useContext, createContext } from 'react';

export interface MCPClient {
  callTool(name: string, arguments: Record<string, any>): Promise<any>;
  listTools(): Promise<string[]>;
  isConnected(): boolean;
}

// Create MCP context
const MCPContext = createContext<MCPClient | null>(null);

export const MCPProvider = MCPContext.Provider;

/**
 * Use MCP client
 */
export function useMCP(): MCPClient {
  const client = useContext(MCPContext);

  if (!client) {
    throw new Error('useMCP must be used within MCPProvider');
  }

  return client;
}

/**
 * Create MCP client (example implementation)
 *
 * Replace with your actual MCP client logic.
 */
export function createMCPClient(serverUrl: string): MCPClient {
  let connected = false;

  // Initialize connection (replace with actual MCP protocol)
  const connect = async () => {
    try {
      const response = await fetch(`${serverUrl}/health`);
      connected = response.ok;
    } catch (error) {
      console.error('Failed to connect to MCP server:', error);
      connected = false;
    }
  };

  connect();

  return {
    async callTool(name: string, args: Record<string, any>): Promise<any> {
      try {
        const response = await fetch(`${serverUrl}/tools/${name}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(args),
        });

        if (!response.ok) {
          throw new Error(`MCP tool call failed: ${response.statusText}`);
        }

        const result = await response.json();
        return result;
      } catch (error) {
        console.error(`Error calling tool ${name}:`, error);
        throw error;
      }
    },

    async listTools(): Promise<string[]> {
      try {
        const response = await fetch(`${serverUrl}/tools`);
        if (!response.ok) {
          throw new Error('Failed to list tools');
        }
        const tools = await response.json();
        return tools.map((t: any) => t.name);
      } catch (error) {
        console.error('Error listing tools:', error);
        return [];
      }
    },

    isConnected(): boolean {
      return connected;
    },
  };
}

/**
 * Example usage in your app:
 *
 * import { MCPProvider, createMCPClient } from './hooks/useMCP';
 *
 * const mcpClient = createMCPClient('http://localhost:8765');
 *
 * function App() {
 *   return (
 *     <MCPProvider value={mcpClient}>
 *       <YourApp />
 *     </MCPProvider>
 *   );
 * }
 */
