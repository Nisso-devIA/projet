declare module "page-flip" {
  export class PageFlip {
    constructor(element: HTMLElement, options: Record<string, unknown>);
    loadFromHTML(pages: HTMLElement[]): void;
    destroy(): void;
    flipNext(corner?: string): void;
    flipPrev(corner?: string): void;
    getCurrentPageIndex(): number;
    on(event: string, cb: (e: { data: number | { page?: number } }) => void): void;
    update(): void;
  }
}
