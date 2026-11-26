import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: { colors: { forest: "#214E42", pine: "#173A32", ivory: "#F7F6F0", sage: "#E7EFE8", amber: "#E9B96C", terracotta: "#C9795B", ink: "#252C29", muted: "#78817B", line: "#E7E6DE" }, fontFamily: { sans: ["Arial", "sans-serif"], editorial: ["Georgia", "serif"] } } },
  plugins: [],
};
export default config;
