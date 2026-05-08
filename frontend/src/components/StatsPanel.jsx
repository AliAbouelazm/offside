import styles from './StatsPanel.module.css'

export default function StatsPanel({ summary }) {
  const s = summary

  return (
    <div className={styles.panel}>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Formations</h3>
        <div className={styles.row}>
          <StatCard
            label="Home Formation"
            value={s.avg_formation_home}
            color="var(--home)"
          />
          <StatCard
            label="Away Formation"
            value={s.avg_formation_away}
            color="var(--away)"
          />
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Space Control</h3>
        <SpaceBar home={s.avg_space_control_home} away={s.avg_space_control_away} />
        <div className={styles.row}>
          <StatCard label="Home" value={`${s.avg_space_control_home}%`} color="var(--home)" />
          <StatCard label="Away" value={`${s.avg_space_control_away}%`} color="var(--away)" />
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Pressing</h3>
        <div className={styles.row}>
          <StatCard label="Avg Press Score" value={s.avg_pressing_score} color="var(--accent)" />
          <StatCard label="Peak Press Score" value={s.peak_pressing_score} color="#f59e0b" />
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Player Spread (avg inter-player distance)</h3>
        <div className={styles.row}>
          <StatCard
            label="Home"
            value={`${s.avg_inter_player_dist_home}m`}
            color="var(--home)"
          />
          <StatCard
            label="Away"
            value={`${s.avg_inter_player_dist_away}m`}
            color="var(--away)"
          />
        </div>
      </div>

      <div className={styles.footer}>
        <span className={styles.footerStat}>
          {s.total_frames_analyzed} frames analyzed
        </span>
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statValue} style={{ color }}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  )
}

function SpaceBar({ home, away }) {
  return (
    <div className={styles.spaceBar}>
      <div
        className={styles.spaceHome}
        style={{ width: `${home}%` }}
      />
      <div
        className={styles.spaceAway}
        style={{ width: `${away}%` }}
      />
    </div>
  )
}
