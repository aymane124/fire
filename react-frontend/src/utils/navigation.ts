import { useNavigate } from 'react-router-dom';

let navigateFunction: ((path: string) => void) | null = null;

export const setNavigate = (navigate: (path: string) => void) => {
  navigateFunction = navigate;
};

export const navigateTo = (path: string) => {
  if (navigateFunction) {
    navigateFunction(path);
  } else {
    // Fallback to window.location if navigate is not set
    window.location.href = path;
  }
}; 