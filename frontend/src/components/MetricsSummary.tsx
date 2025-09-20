import { SimpleGrid, Stat, StatLabel, StatNumber, useColorModeValue } from '@chakra-ui/react';

import type { Property } from '../types/property';

interface MetricsSummaryProps {
  data: Property[];
  total: number;
}

const formatNumber = (value: number) =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(value));

const median = (values: number[]) => {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
};

export const MetricsSummary = ({ data, total }: MetricsSummaryProps) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  if (data.length === 0) {
    return null;
  }

  const averageScore = data.reduce((sum, property) => sum + property.listing_score, 0) / data.length;
  const averageEquity = data.reduce((sum, property) => sum + (property.equity_available ?? 0), 0) / data.length;
  const valueGaps = data.map((property) => property.value_gap ?? 0).filter((value) => value > 0);
  const medianValueGap = median(valueGaps);
  const absenteeShare =
    (data.filter((property) => property.owner_occupancy === 'absentee').length / data.length) * 100;
  const topScore = Math.max(...data.map((property) => property.listing_score));

  return (
    <SimpleGrid columns={{ base: 1, md: 2, xl: 3, '2xl': 6 }} spacing={4}>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Properties Matched</StatLabel>
        <StatNumber>{formatNumber(total)}</StatNumber>
      </Stat>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Average Listing Score</StatLabel>
        <StatNumber>{averageScore.toFixed(1)}</StatNumber>
      </Stat>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Average Equity</StatLabel>
        <StatNumber>{`$${formatNumber(averageEquity)}`}</StatNumber>
      </Stat>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Median Value Gap</StatLabel>
        <StatNumber>{valueGaps.length ? `$${formatNumber(medianValueGap)}` : '--'}</StatNumber>
      </Stat>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Absentee Share</StatLabel>
        <StatNumber>{`${absenteeShare.toFixed(0)}%`}</StatNumber>
      </Stat>
      <Stat bg={cardBg} p={4} borderRadius="lg" boxShadow="sm">
        <StatLabel color="gray.500">Top Listing Score</StatLabel>
        <StatNumber>{topScore.toFixed(1)}</StatNumber>
      </Stat>
    </SimpleGrid>
  );
};
