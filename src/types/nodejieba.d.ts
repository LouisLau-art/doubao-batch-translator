declare module 'nodejieba' {
  interface NodeJiebaOptions {
    dict?: string;
    hmmDict?: string;
    userDict?: string;
    idfDict?: string;
    stopWordDict?: string;
  }

  export function load(options: NodeJiebaOptions): void;
  export function cut(text: string, hmm?: boolean): string[];
  export function cutAll(text: string): string[];
  export function cutForSearch(text: string, hmm?: boolean): string[];
  export function tag(text: string): Array<[string, string]>;
  export function extract(text: string, topN: number): Array<[string, number]>;
  export function textrank(text: string, topN: number): Array<[string, number]>;
}