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
} from '@chakra-ui/react';
import { FiRefreshCw } from 'react-icons/fi';

import { usePropertiesQuery } from '../api/hooks';
import { ExportButton } from '../components/ExportButton';
import { FilterBar } from '../components/FilterBar';
import { MetricsSummary } from '../components/MetricsSummary';
import { PropertyTable } from '../components/PropertyTable';
import { usePropertyFilters } from '../store/filterStore';

export const Dashboard = () => {
  const { filters } = usePropertyFilters();
  const { data, error, isLoading, isFetching, refetch } = usePropertiesQuery(filters);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

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

          <Flex align="center">
            <HStack spacing={3}>
              <Button leftIcon={<FiRefreshCw />} variant="ghost" onClick={() => refetch()} isLoading={isFetching}>
                Refresh
              </Button>
              <ExportButton />
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
    </Box>
  );
};
