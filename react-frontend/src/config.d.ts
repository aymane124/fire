export const API_URL: string;
export const config: {
    isDevelopment: boolean;
    showDevTools: boolean;
};
export const API_ENDPOINTS: {
    CAMERAS: {
        LIST: string;
        UPLOAD: string;
        DETAIL: (id: string) => string;
    };
    COMMANDS: {
        SAVE_CONFIG: string;
        EXECUTE: string;
    };
    AUTH: {
        LOGIN: string;
        REFRESH: string;
    };
}; 