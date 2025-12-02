declare module 'tiktoken' {
  export function get_encoding(encodingName: string): {
    encode: (text: string) => number[];
    decode: (tokens: number[]) => string;
  };
}