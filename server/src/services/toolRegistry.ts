export interface ToolParameter {
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  required: boolean;
  default?: any;
  description?: string;
}

export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, ToolParameter>;
  execute: (params: any) => Promise<string>;
}

export class ToolRegistry {
  private tools: Map<string, Tool>;
  
  constructor() {
    this.tools = new Map();
  }
  
  public registerTool(tool: Tool): void {
    this.tools.set(tool.name.toLowerCase(), tool);
  }
  
  public getTool(name: string): Tool | undefined {
    return this.tools.get(name.toLowerCase());
  }
  
  public getToolNames(): string[] {
    return Array.from(this.tools.keys());
  }
  
  public getAllTools(): Tool[] {
    return Array.from(this.tools.values());
  }
  
  public removeTool(name: string): boolean {
    return this.tools.delete(name.toLowerCase());
  }
} 