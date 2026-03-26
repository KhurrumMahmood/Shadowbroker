import type { Preview } from "@storybook/react";
import "../src/design/artifact-tokens.css";

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: "dark",
      values: [
        { name: "dark", value: "#000000" },
        { name: "panel", value: "rgb(5, 5, 8)" },
      ],
    },
  },
};

export default preview;
