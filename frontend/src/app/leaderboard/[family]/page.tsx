import { ComingSoon } from "@/components/coming-soon";

const FAMILY_NAME: Record<string, string> = {
  claude: "Claude 榜",
  gpt: "GPT 榜",
  gemini: "Gemini 榜",
};

export default async function LeaderboardFamilyPage({
  params,
}: {
  params: Promise<{ family: string }>;
}) {
  const { family } = await params;
  const name = FAMILY_NAME[family] ?? "排行榜";
  return <ComingSoon title={name} desc={`${name}正在建设中，敬请期待。`} />;
}
