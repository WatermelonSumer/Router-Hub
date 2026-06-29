import { redirect } from "next/navigation";

// /rank 默认进入 Claude 榜（三榜中编程/Agent 用户最关注的入口）
export default function RankIndexPage() {
  redirect("/rank/claude");
}
