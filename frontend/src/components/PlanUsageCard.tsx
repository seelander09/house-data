import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Flex,
  Heading,
  Progress,
  SimpleGrid,
  Skeleton,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';

import type { PlanSnapshot, PlanQuota } from '../types/usage';

interface PlanUsageCardProps {
  plan?: PlanSnapshot;
  isLoading: boolean;
}

const formatQuotaLabel = (quota: PlanQuota) => {
  if (quota.event_type === 'properties.export') return 'CSV Exports';
  if (quota.event_type === 'properties.lead_pack') return 'Lead Packs';
  if (quota.event_type === 'properties.refresh_cache') return 'Cache Refreshes';
  return quota.event_type;
};

const usagePercent = (quota: PlanQuota) => {
  if (!quota.limit) return 0;
  return Math.min(100, Math.round((quota.used / quota.limit) * 100));
};

const statusColor = (status: PlanQuota['status']) => {
  if (status === 'limit') return 'red';
  if (status === 'warning') return 'orange';
  return 'green';
};

export const PlanUsageCard = ({ plan, isLoading }: PlanUsageCardProps) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  if (isLoading) {
    return <Skeleton height="140px" borderRadius="lg" />;
  }

  if (!plan || plan.quotas.length === 0) {
    return null;
  }

  return (
    <Box bg={cardBg} borderRadius="lg" boxShadow="sm" p={5}>
      <Flex align={{ base: 'flex-start', md: 'center' }} justify="space-between" mb={4} gap={3} wrap="wrap">
        <Box>
          <Heading size="sm">Plan usage</Heading>
          <Text fontSize="sm" color="gray.500">
            {plan.plan_display_name} · rolling {plan.quotas[0]?.window_days ?? 30}-day window
          </Text>
        </Box>
        <Badge colorScheme="purple">{plan.plan_name}</Badge>
      </Flex>

      <SimpleGrid columns={{ base: 1, md: plan.quotas.length }} spacing={4}>
        {plan.quotas.map((quota) => (
          <Stat key={quota.event_type} borderWidth="1px" borderRadius="md" p={4}>
            <StatLabel>{formatQuotaLabel(quota)}</StatLabel>
            <StatNumber fontSize="lg">
              {quota.used} / {quota.limit}
            </StatNumber>
            <StatHelpText>
              {quota.remaining} remaining · {quota.window_days}-day limit
            </StatHelpText>
            <Progress
              mt={2}
              value={usagePercent(quota)}
              colorScheme={statusColor(quota.status)}
              size="sm"
              borderRadius="full"
            />
          </Stat>
        ))}
      </SimpleGrid>

      {plan.alerts.length > 0 && (
        <Box mt={4}>
          {plan.alerts.map((alert) => (
            <Alert
              key={`${alert.event_type}-${alert.status}`}
              status={alert.status === 'limit' ? 'error' : 'warning'}
              borderRadius="md"
              mb={2}
            >
              <AlertIcon />
              {alert.message}
            </Alert>
          ))}
        </Box>
      )}
    </Box>
  );
};
