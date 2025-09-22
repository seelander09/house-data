import { useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Container,
  Flex,
  Heading,
  HStack,
  Spacer,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { FiRefreshCw, FiSend, FiTarget } from 'react-icons/fi';

import { usePlanSnapshotQuery, usePropertiesQuery } from '../api/hooks';
import { ExportButton } from '../components/ExportButton';
import { FilterBar } from '../components/FilterBar';
import { LeadPackPanel } from '../components/LeadPackPanel';
import { MetricsSummary } from '../components/MetricsSummary';
import { OutreachDrawer } from '../components/OutreachDrawer';
import { PlanUsageCard } from '../components/PlanUsageCard';
import { PropertyTable } from '../components/PropertyTable';
import { usePropertyFilters } from '../store/filterStore';
import { useDebouncedValue } from '../hooks/useDebouncedValue';

export const Dashboard = () => {
  const { filters } = usePropertyFilters();
  const debouncedFilters = useDebouncedValue(filters, 350);
  const { isOpen: isLeadPackOpen, onOpen: openLeadPack, onClose: closeLeadPack } = useDisclosure();
  const { isOpen: isOutreachOpen, onOpen: openOutreach, onClose: closeOutreach } = useDisclosure();

  const { data, error, isLoading, isFetching, refetch } = usePropertiesQuery(debouncedFilters);
  const { data: planSnapshot, isLoading: isPlanLoading } = usePlanSnapshotQuery();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const leadPackQuota = planSnapshot?.quotas.find((quota) => quota.event_type === 'properties.lead_pack');
  const leadPackLimitReached = (leadPackQuota?.remaining ?? 1) <= 0;

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="7xl">
        <Flex direction="column" gap={6}>
          <Box>
            <Heading as="h1" size="lg" mb={2}>
              Realtor Lead Radar
            </Heading>
            <Text color="gray.600">
              Discover high-equity properties before your competitors and reach owners with confidence.
            </Text>
          </Box>

          <FilterBar />

          <PlanUsageCard plan={planSnapshot} isLoading={isPlanLoading} />

          <Flex align="center" wrap="wrap" gap={3}>
            <HStack spacing={3}>
              <Button leftIcon={<FiRefreshCw />} variant="ghost" onClick={() => refetch()} isLoading={isFetching}>
                Refresh
              </Button>
              <ExportButton />
              <Button
                leftIcon={<FiTarget />}
                variant="outline"
                onClick={openLeadPack}
                isDisabled={leadPackLimitReached}
                title={leadPackLimitReached ? 'Lead pack quota reached for your plan' : undefined}
              >
                Lead packs
              </Button>
              <Button leftIcon={<FiSend />} variant="outline" onClick={openOutreach}>
                Outreach scripts
              </Button>
            </HStack>
            <Spacer />
            <Text color="gray.500" fontSize="sm">
              API filters applied automatically. Adjust filters above to refine your lead list.
            </Text>
          </Flex>

          {error ? (
            <Alert status="error" borderRadius="lg">
              <AlertIcon />
              <AlertTitle mr={2}>Unable to load properties.</AlertTitle>
              <AlertDescription>Please verify your API key and try again.</AlertDescription>
            </Alert>
          ) : null}

          <MetricsSummary data={items} total={total} />

          <PropertyTable data={items} total={total} isLoading={isLoading || isFetching} />
        </Flex>
      </Container>

      <LeadPackPanel isOpen={isLeadPackOpen} onClose={closeLeadPack} filters={debouncedFilters} />
      <OutreachDrawer isOpen={isOutreachOpen} onClose={closeOutreach} filters={debouncedFilters} properties={items} />
    </Box>
  );
};
