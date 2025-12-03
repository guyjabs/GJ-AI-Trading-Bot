import { DashboardLayout } from "@/components/dashboard-layout"
import { PortfolioOverview } from "@/components/portfolio-overview"
import { StrategyScreener } from "@/components/strategy-screener"
import { RiskManagement } from "@/components/risk-management"
import { BotActivityTerminal } from "@/components/bot-activity-terminal"
import { MarketTicker } from "@/components/market-ticker"
import { QuickTrade } from "@/components/quick-trade"

export default function Dashboard() {
  return (
    <DashboardLayout>
      <div className="flex flex-col gap-4 p-4 lg:p-6">
        <MarketTicker />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <PortfolioOverview />
          </div>
          <div>
            <QuickTrade />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <StrategyScreener />
          <RiskManagement />
        </div>

        <BotActivityTerminal />
      </div>
    </DashboardLayout>
  )
}
