import {
  Badge,
  Box,
  Divider,
  Heading,
  HStack,
  Skeleton,
  Stack,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useColorModeValue,
} from '@chakra-ui/react';

import { useUsageAlertsQuery, useUsageHistoryQuery } from '../api/hooks';

interface UsageInsightsCardProps {
  historyDays?: number;
  alertLimit?: number;
}

const dayFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });
const dateTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const formatDate = (isoDate: string) => dayFormatter.format(new Date(isoDate));
const formatDateTime = (isoDateTime: string) => dateTimeFormatter.format(new Date(isoDateTime));

export const UsageInsightsCard = ({ historyDays = 14, alertLimit = 5 }: UsageInsightsCardProps) => {
  const cardBg = useColorModeValue('white', 'gray.900');
  const tableBg = useColorModeValue('gray.50', 'gray.800');
  const { data: history, isLoading: isHistoryLoading } = useUsageHistoryQuery(historyDays);
  const { data: alerts, isLoading: isAlertsLoading } = useUsageAlertsQuery(alertLimit);

  return (
    <Box borderWidth="1px" borderRadius="lg" p={5} boxShadow="sm" bg={cardBg}>
      <Stack spacing={4}>
        <Heading size="sm">Usage insights</Heading>

        <Box>
          <HStack justify="space-between" mb={2}>
            <Text fontWeight="semibold">Recent activity</Text>
            <Badge colorScheme="blue">{historyDays}-day window</Badge>
          </HStack>
          {isHistoryLoading ? (
            <Skeleton height="120px" borderRadius="md" />
          ) : history && history.length > 0 ? (
            <Table size="sm" variant="simple" bg={tableBg} borderRadius="md" overflow="hidden">
              <Thead>
                <Tr>
                  <Th>Date</Th>
                  <Th>Event</Th>
                  <Th isNumeric>Count</Th>
                </Tr>
              </Thead>
              <Tbody>
                {history.map((entry) => (
                  <Tr key={`${entry.date}-${entry.event_type}`}>
                    <Td>{formatDate(entry.date)}</Td>
                    <Td>{entry.event_type}</Td>
                    <Td isNumeric>{entry.count}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          ) : (
            <Text fontSize="sm" color="gray.500">
              No metered activity yet.
            </Text>
          )}
        </Box>

        <Divider />

        <Box>
          <HStack justify="space-between" mb={2}>
            <Text fontWeight="semibold">Alerts</Text>
            <Badge colorScheme="purple">Last {alertLimit}</Badge>
          </HStack>
          {isAlertsLoading ? (
            <Skeleton height="96px" borderRadius="md" />
          ) : alerts && alerts.length > 0 ? (
            <Stack spacing={3}>
              {alerts.map((alert) => (
                <Box
                  key={`${alert.event_type}-${alert.created_at}`}
                  borderWidth="1px"
                  borderRadius="md"
                  p={3}
                  borderColor={alert.status === 'limit' ? 'red.400' : 'orange.300'}
                >
                  <Text fontWeight="semibold">{alert.event_type}</Text>
                  <Text fontSize="sm" color="gray.600">
                    {formatDateTime(alert.created_at)}
                  </Text>
                  <Text mt={1}>{alert.message}</Text>
                </Box>
              ))}
            </Stack>
          ) : (
            <Text fontSize="sm" color="gray.500">
              No alerts raised in this window.
            </Text>
          )}
        </Box>
      </Stack>
    </Box>
  );
};
