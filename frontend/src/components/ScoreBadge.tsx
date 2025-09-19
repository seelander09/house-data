import { Badge, Tooltip } from '@chakra-ui/react';

import type { ScoreBreakdown } from '../types/property';

const scoreColor = (score: number) => {
  if (score >= 85) return 'green';
  if (score >= 70) return 'yellow';
  if (score >= 55) return 'orange';
  return 'red';
};

interface ScoreBadgeProps {
  score: number;
  breakdown: ScoreBreakdown;
}

export const ScoreBadge = ({ score, breakdown }: ScoreBadgeProps) => {
  const tooltip = `Equity: ${(breakdown.equity * 100).toFixed(0)}% | Value Gap: ${(breakdown.value_gap * 100).toFixed(0)}% | Recency: ${(breakdown.recency * 100).toFixed(0)}%`;
  return (
    <Tooltip label={tooltip} hasArrow>
      <Badge colorScheme={scoreColor(score)} fontSize="md" px={3} py={1} borderRadius="full">
        {score.toFixed(1)}
      </Badge>
    </Tooltip>
  );
};
