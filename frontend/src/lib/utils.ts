import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合并 Tailwind class，处理条件类名与冲突类名去重。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
