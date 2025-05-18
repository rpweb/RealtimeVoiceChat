/**
 * Custom stream parser for handling the text response format.
 * This function creates a custom stream parser for the Vercel AI SDK
 * that can handle plain text or the special protocol format.
 */
export function createParser() {
  return (data: string): string => {
    // Check if the data is in the special protocol format (with the number prefix)
    const match = /^\d+:"(.+)"$/.exec(data.trim());
    
    if (match && match[1]) {
      // If it matches the protocol format, extract the actual text content
      return match[1];
    }
    
    // If not in protocol format, return the raw text
    return data;
  };
} 