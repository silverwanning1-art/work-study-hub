export type Workspace = 'studium' | 'arbeit';

export interface PluginInfo {
	id: string;
	type: string;
	version: string;
	description: string;
	workspaces: string[];
}

export interface AgentInfo {
	id: string;
	description: string;
	workspaces: string[];
}

export interface Registry {
	plugins: PluginInfo[];
	agents: AgentInfo[];
}

export async function loadRegistry(fetchFn: typeof fetch = fetch): Promise<Registry> {
	const response = await fetchFn('/api/registry');
	if (!response.ok) {
		throw new Error(`Registry request failed with status ${response.status}`);
	}
	return (await response.json()) as Registry;
}

/** A plugin or agent is shown in a workspace if it targets it or is global. */
export function visibleIn(item: { workspaces: string[] }, workspace: Workspace): boolean {
	return item.workspaces.includes(workspace) || item.workspaces.includes('global');
}
