import { API_URL } from '../config';

export interface WebSocketMessage {
    type: 'command' | 'output' | 'error' | 'system' | 'connect' | 'disconnect' | 'connect_ssh' | 'disconnect_ssh' | 'command_status' | 'pager' | 'pager_action';
    content?: string;
    command?: string;
    command_id?: string;
    firewallId?: string;
    status?: string;
    error?: string;
    action?: 'page' | 'line' | 'quit';
}

export class WebSocketService {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private onMessageCallback: ((message: WebSocketMessage) => void) | null = null;
    private onConnectCallback: (() => void) | null = null;
    private onDisconnectCallback: (() => void) | null = null;
    private onErrorCallback: ((error: Event) => void) | null = null;
    private isManuallyDisconnected = false; // Flag to prevent auto-reconnect on manual disconnect

    constructor(
        private firewallId: string,
        private baseUrl: string = API_URL.replace('http', 'ws').replace('/api', '')
    ) {}

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                // Reset manual disconnect flag
                this.isManuallyDisconnected = false;
                
                const token = localStorage.getItem('token');
                const wsUrl = `${this.baseUrl}/ws/terminal/${this.firewallId}/?token=${token}`;
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    if (this.onConnectCallback) {
                        this.onConnectCallback();
                    }
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message: WebSocketMessage = JSON.parse(event.data);
                        if (this.onMessageCallback) {
                            this.onMessageCallback(message);
                        }
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket disconnected:', event.code, event.reason);
                    if (this.onDisconnectCallback) {
                        this.onDisconnectCallback();
                    }
                    
                    // Attempt to reconnect only if not manually disconnected
                    if (!this.isManuallyDisconnected && event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.reconnectAttempts++;
                        setTimeout(() => {
                            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                            this.connect();
                        }, this.reconnectDelay * this.reconnectAttempts);
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    if (this.onErrorCallback) {
                        this.onErrorCallback(error);
                    }
                    reject(error);
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    disconnect(): void {
        this.isManuallyDisconnected = true; // Set flag before disconnecting
        if (this.ws) {
            this.ws.close(1000, 'Manual disconnect');
            this.ws = null;
        }
    }

    sendCommand(command: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message: WebSocketMessage = {
                type: 'command',
                command: command,
                command_id: crypto.randomUUID(), // Generate unique command ID
                firewallId: this.firewallId
            };
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    sendMessage(message: WebSocketMessage): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    onMessage(callback: (message: WebSocketMessage) => void): void {
        this.onMessageCallback = callback;
    }

    onConnect(callback: () => void): void {
        this.onConnectCallback = callback;
    }

    onDisconnect(callback: () => void): void {
        this.onDisconnectCallback = callback;
    }

    onError(callback: (error: Event) => void): void {
        this.onErrorCallback = callback;
    }

    isConnected(): boolean {
        return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }

    getReadyState(): number {
        return this.ws ? this.ws.readyState : WebSocket.CLOSED;
    }
}

export const createWebSocketService = (firewallId: string): WebSocketService => {
    return new WebSocketService(firewallId);
};
