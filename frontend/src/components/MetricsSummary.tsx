import { SimpleGrid, Stat, StatLabel, StatNumber, useColorModeValue } from '@chakra-ui/react';

import type { Property } from '../types/property';

interface MetricsSummaryProps {
  data: Property[];
  total: number;
}

const formatNumber = (value: number) =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(value));

export const MetricsSummary = ({ data, total }: MetricsSummaryProps) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  if (data.length === 0) {
    return null;
  }

  const averageScore = data.reduce((sum, property) => sum + property.listing_score, 0) / data.length;
  const averageEquity = data.reduce((sum, property) => sum + (property.equity_available ?? 0), 0) / data.length;
  const topScore = Math.max(...data.map((property) => property.listing_score));

  return (
    <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing={4}>
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
        <StatLabel color="gray.500">Top Listing Score</StatLabel>
        <StatNumber>{topScore.toFixed(1)}</StatNumber>
      </Stat>
    </SimpleGrid>
  );
};
