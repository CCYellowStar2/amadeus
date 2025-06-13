/// <reference types="vite/client" />

declare global {
  interface Window {
    api?: {
      invoke: (channel: string, ...args: any[]) => Promise<any>;
      receive: (channel: string, listener: (...args: any[]) => void) => (() => void) | undefined;
    }
  }
}