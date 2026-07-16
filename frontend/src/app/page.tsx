"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { motion } from "motion/react";

const EASE = [0.16, 1, 0.3, 1] as const;

export default function Home() {
  return (
    <main className="landing-hero">
      <motion.div
        className="landing-video-wrap"
        initial={{ opacity: 0, scale: 1.05 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.8, ease: EASE }}
        aria-hidden="true"
      >
        <video
          className="landing-video"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260508_215831_c6a8989c-d716-4d8d-8745-e972a2eec711.mp4"
          autoPlay
          muted
          loop
          playsInline
        />
      </motion.div>

      <motion.nav
        className="landing-nav"
        initial={{ y: -16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: EASE }}
        aria-label="首页导航"
      >
        <div className="landing-nav-group">
          <Link className="landing-brand" href="/" aria-label="Quant Platform 首页">
            <svg className="landing-mark" viewBox="0 0 28 28" aria-hidden="true">
              <rect x="4" y="7" width="15" height="6" rx="3" transform="rotate(-35 4 7)" />
              <rect x="10" y="16" width="15" height="6" rx="3" transform="rotate(-35 10 16)" />
            </svg>
            <span>Quant Platform</span>
          </Link>

          <Link className="landing-menu-pill" href="/market">
            <span className="landing-menu-icon">
              <Plus size={12} strokeWidth={3} />
            </span>
            <span>进入平台</span>
          </Link>

          <div className="landing-tags-pill" aria-label="核心能力">
            <span>策略回测</span>
            <span>模拟交易</span>
          </div>
        </div>

        <Link className="landing-system-pill" href="/market?panel=alerts">
          <span className="landing-grid-icon" aria-hidden="true">
            <svg viewBox="0 0 14 14">
              <circle cx="4" cy="4" r="1.25" />
              <circle cx="10" cy="4" r="1.25" />
              <circle cx="4" cy="10" r="1.25" />
              <circle cx="10" cy="10" r="1.25" />
            </svg>
          </span>
          <span className="landing-system-label">AI 事件研究</span>
        </Link>
      </motion.nav>

      <motion.footer
        className="landing-footer"
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.5, duration: 1, ease: EASE }}
      >
        <div className="landing-copy">
          <motion.p
            className="landing-subtitle"
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.8, ease: EASE }}
          >
            <span />
            可信数据驱动的 A 股量化平台
          </motion.p>

          <motion.h1
            className="landing-heading"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.8, ease: EASE }}
          >
            从市场信号
            <br />
            到真实约束。
          </motion.h1>

          <motion.div
            className="landing-actions"
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 1, duration: 0.8, ease: EASE }}
          >
            <Link className="landing-primary-action" href="/market">
              查看行情
            </Link>
            <Link className="landing-secondary-action" href="/strategies/new">
              创建策略
            </Link>
          </motion.div>
        </div>

        <div className="landing-capability-tags" aria-label="平台能力">
          <span>前复权</span>
          <span>T+1 模拟</span>
          <span>事件分析</span>
        </div>
      </motion.footer>
    </main>
  );
}
