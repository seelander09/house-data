import { useMemo, useState, type ReactNode } from 'react';
import {
  Badge,
  Box,
  Button,
  Divider,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  Heading,
  HStack,
  NumberInput,
  NumberInputField,
  Select,
  Spinner,
  Stack,
  Text,
  useToast,
} from '@chakra-ui/react';
import { FiDownload } from 'react-icons/fi';

import { useExportProperties, useLeadPacksQuery } from '../api/hooks';
import type { PropertyFilters } from '../types/property';

const groupOptions = [
  { label: 'Postal code', value: 'postal_code' },
  { label: 'City', value: 'city' },
  { label: 'State', value: 'state' },
];

interface LeadPackPanelProps {
  isOpen: boolean;
  onClose: () => void;
  filters: PropertyFilters;
}

const formatCurrency = (value: number | null | undefined) =>
  value == null ? '--' : `$${Math.round(value).toLocaleString()}`;

export const LeadPackPanel = ({ isOpen, onClose, filters }: LeadPackPanelProps) => {
  const toast = useToast();
  const exportMutation = useExportProperties();
  const [groupBy, setGroupBy] = useState<string>('postal_code');
  const [packSize, setPackSize] = useState(50);

  const normalizedFilters = useMemo<PropertyFilters>(
    () => ({
      ...filters,
      limit: Math.max(filters.limit ?? 50, 500),
      offset: 0,
    }),
    [filters],
  );

  const { data, isLoading, isFetching } = useLeadPacksQuery(normalizedFilters, groupBy, packSize, isOpen);

  const handleExportPack = async (label: string) => {
    const payload: Partial<PropertyFilters> = {
      ...filters,
      limit: packSize,
      offset: 0,
    };

    if (groupBy === 'postal_code') payload.postal_code = label;
    if (groupBy === 'city') payload.city = label;
    if (groupBy === 'state') payload.state = label;

    try {
      const count = await exportMutation.mutateAsync(payload);
      toast({
        title: 'Lead pack export started',
        description: `Launching CSV download for ${count} properties in ${label}.`,
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({ title: 'Export failed', description: 'Unable to export this pack right now.', status: 'error' });
    }
  };

  return (
    <Drawer isOpen={isOpen} placement="right" size="lg" onClose={onClose}>
      <DrawerOverlay />
      <DrawerContent>
        <DrawerHeader borderBottomWidth="1px">
          Monetise Lead Packs
        </DrawerHeader>
        <DrawerBody>
          <Stack spacing={6}>
            <Flex gap={4} wrap="wrap" align="flex-end">
              <FormControlGroup label="Group by">
                <Select value={groupBy} onChange={(event) => setGroupBy(event.target.value)} maxW="200px">
                  {groupOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </FormControlGroup>
              <FormControlGroup label="Top listings per pack">
                <NumberInput value={packSize} min={10} max={500} onChange={(_s, value) => setPackSize(() => {\n                  if (Number.isNaN(value)) return 50;\n                  return Math.min(500, Math.max(10, Math.round(value)));\n                })}>
                  <NumberInputField />
                </NumberInput>
              </FormControlGroup>
              {isFetching && (
                <HStack color="gray.500">
                  <Spinner size="sm" />
                  <Text fontSize="sm">Refreshing packs…</Text>
                </HStack>
              )}
            </Flex>

            {isLoading ? (
              <Flex align="center" justify="center" h="200px" direction="column" gap={3}>
                <Spinner size="lg" />
                <Text color="gray.500">Crunching scores…</Text>
              </Flex>
            ) : !data || data.packs.length === 0 ? (
              <Text color="gray.500">No lead packs match the current filters.</Text>
            ) : (
              <Stack spacing={6}>
                {data.packs.map((pack) => {
                  const absenteeCount = pack.top_properties.filter((property) => property.owner_occupancy === 'absentee').length;
                  return (
                    <Box key={pack.label} borderWidth="1px" borderRadius="lg" p={4} boxShadow="sm">
                      <Flex justify="space-between" align="center" mb={3} wrap="wrap" gap={2}>
                        <Heading size="sm">{pack.label || 'Unclassified market'}</Heading>
                        <HStack spacing={2}>
                          <Badge colorScheme="purple">{pack.total} matches</Badge>
                          <Badge colorScheme="orange">{absenteeCount} absentee</Badge>
                          <Button
                            size="sm"
                            leftIcon={<FiDownload />}
                            onClick={() => handleExportPack(pack.label)}
                            isLoading={exportMutation.isPending}
                          >
                            Export pack
                          </Button>
                        </HStack>
                      </Flex>
                      <Divider mb={3} />
                      <Stack spacing={3}>
                        {pack.top_properties.slice(0, 5).map((property) => (
                          <Box key={property.property_id} borderWidth="1px" borderRadius="md" p={3}>
                            <Flex justify="space-between" wrap="wrap" gap={3}>
                              <Box>
                                <Text fontWeight="semibold">{property.address ?? 'Address unavailable'}</Text>
                                <Text fontSize="sm" color="gray.500">
                                  {[property.city, property.state, property.postal_code].filter(Boolean).join(', ')}
                                </Text>
                              </Box>
                              <HStack spacing={3}>
                                {property.owner_occupancy && (
                                  <Badge colorScheme={property.owner_occupancy === 'absentee' ? 'orange' : 'green'}>
                                    {property.owner_occupancy === 'absentee' ? 'Absentee' : 'Owner occupied'}
                                  </Badge>
                                )}
                                <Badge colorScheme="blue">Score {property.listing_score.toFixed(1)}</Badge>
                              </HStack>
                            </Flex>
                            <HStack spacing={6} mt={2} fontSize="sm" color="gray.600">
                              <Text>Equity {formatCurrency(property.equity_available)}</Text>
                              <Text>Value gap {formatCurrency(property.value_gap ?? null)}</Text>
                              {property.distance_from_search_center_miles != null && (
                                <Text>{property.distance_from_search_center_miles.toFixed(1)} mi from center</Text>
                              )}
                            </HStack>
                          </Box>
                        ))}
                      </Stack>
                    </Box>
                  );
                })}
              </Stack>
            )}
          </Stack>
        </DrawerBody>
        <DrawerFooter borderTopWidth="1px">
          <Text fontSize="sm" color="gray.500">
            Generated at {data ? new Date(data.generated_at).toLocaleString() : '--'}
          </Text>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};

interface FormControlGroupProps {
  label: string;
  children: ReactNode;
}

const FormControlGroup = ({ label, children }: FormControlGroupProps) => (
  <Stack spacing={1}>
    <Text fontSize="sm" color="gray.600">
      {label}
    </Text>
    {children}
  </Stack>
);
