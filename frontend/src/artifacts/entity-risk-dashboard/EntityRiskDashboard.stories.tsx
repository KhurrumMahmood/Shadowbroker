import type { Meta, StoryObj } from "@storybook/react";
import EntityRiskDashboard from "./EntityRiskDashboard";
import mockData from "./mock-data.json";

const meta: Meta<typeof EntityRiskDashboard> = {
  title: "Artifacts/EntityRiskDashboard",
  component: EntityRiskDashboard,
};

export default meta;
type Story = StoryObj<typeof EntityRiskDashboard>;

export const Default: Story = {
  args: {
    initialData: mockData,
  },
};

export const Empty: Story = {
  args: {
    initialData: { entities: [] },
  },
};
