import { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Select,
  Skeleton,
  Stack,
  Text,
  useToast,
} from '@chakra-ui/react';

import { usePlanCatalogQuery, usePlanSnapshotQuery, useSelectPlanMutation } from '../api/hooks';

export const PlanManager = () => {
  const toast = useToast();
  const { data: catalog, isLoading: isCatalogLoading } = usePlanCatalogQuery();
  const { data: snapshot, isLoading: isSnapshotLoading } = usePlanSnapshotQuery();
  const selectPlan = useSelectPlanMutation();
  const [selectedPlan, setSelectedPlan] = useState<string>('');

  useEffect(() => {
    if (snapshot?.plan_name) {
      setSelectedPlan(snapshot.plan_name);
    }
  }, [snapshot?.plan_name]);

  useEffect(() => {
    if (!snapshot?.plan_name && catalog && catalog.length > 0) {
      setSelectedPlan(catalog[0].name);
    }
  }, [catalog, snapshot?.plan_name]);

  const activePlan = useMemo(
    () => catalog?.find((plan) => plan.name === snapshot?.plan_name),
    [catalog, snapshot],
  );
  const pendingPlan = useMemo(() => catalog?.find((plan) => plan.name === selectedPlan), [catalog, selectedPlan]);

  const handleApply = async () => {
    if (!selectedPlan) return;
    try {
      await selectPlan.mutateAsync(selectedPlan);
      toast({ title: 'Plan updated', description: `Subscribed to ${selectedPlan}.`, status: 'success', duration: 2500 });
    } catch (error) {
      const description = error instanceof Error ? error.message : 'Unable to update plan right now.';
      toast({ title: 'Plan update failed', description, status: 'error', duration: 3500 });
    }
  };

  if (isCatalogLoading || isSnapshotLoading) {
    return <Skeleton height="160px" borderRadius="lg" />;
  }

  if (!catalog || catalog.length === 0) {
    return null;
  }

  return (
    <Box borderWidth="1px" borderRadius="lg" p={5} boxShadow="sm" bg="white">
      <Stack spacing={4}>
        <Box>
          <Heading size="sm">Plan management</Heading>
          <Text fontSize="sm" color="gray.500">
            Current plan: <strong>{activePlan?.display_name ?? snapshot?.plan_name ?? 'unknown'}</strong>
          </Text>
        </Box>

        <FormControl>
          <FormLabel>Select a plan</FormLabel>
          <Select value={selectedPlan} onChange={(event) => setSelectedPlan(event.target.value)}>
            {catalog.map((plan) => (
              <option key={plan.name} value={plan.name}>
                {plan.display_name} ({plan.price})
              </option>
            ))}
          </Select>
        </FormControl>

        {pendingPlan && (
          <Box fontSize="sm" color="gray.600">
            <Text fontWeight="semibold">{pendingPlan.display_name}</Text>
            <Text>{pendingPlan.description}</Text>
            <Text mt={1}>
              Includes: {Object.entries(pendingPlan.limits)
                .map(([key, value]) => `${key}: ${value}`)
                .join(', ')}
            </Text>
          </Box>
        )}

        <HStack justify="flex-end">
          <Button
            colorScheme="purple"
            onClick={handleApply}
            isLoading={selectPlan.isPending}
            isDisabled={!selectedPlan || selectedPlan === snapshot?.plan_name}
          >
            Apply plan
          </Button>
        </HStack>
      </Stack>
    </Box>
  );
};
