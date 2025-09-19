import type { ChangeEvent } from 'react';
import { Button, Flex, FormControl, FormLabel, Input, NumberInput, NumberInputField, Stack } from '@chakra-ui/react';

import { usePropertyFilters } from '../store/filterStore';

export const FilterBar = () => {
  const { filters, setFilter, reset } = usePropertyFilters();

  const handleText = (key: 'search' | 'city' | 'state') => (event: ChangeEvent<HTMLInputElement>) => {
    setFilter(key, event.target.value);
  };

  return (
    <Stack
      direction={{ base: 'column', md: 'row' }}
      spacing={4}
      w="full"
      align="flex-end"
      bg="white"
      p={4}
      borderRadius="lg"
      boxShadow="sm"
    >
      <FormControl maxW="260px">
        <FormLabel fontSize="sm" color="gray.600">
          Search
        </FormLabel>
        <Input value={filters.search ?? ''} onChange={handleText('search')} placeholder="Address or owner" />
      </FormControl>
      <FormControl maxW="200px">
        <FormLabel fontSize="sm" color="gray.600">
          City
        </FormLabel>
        <Input value={filters.city ?? ''} onChange={handleText('city')} placeholder="City" />
      </FormControl>
      <FormControl maxW="140px">
        <FormLabel fontSize="sm" color="gray.600">
          State
        </FormLabel>
        <Input
          value={filters.state ?? ''}
          onChange={handleText('state')}
          maxLength={2}
          textTransform="uppercase"
          placeholder="TX"
        />
      </FormControl>
      <FormControl maxW="200px">
        <FormLabel fontSize="sm" color="gray.600">
          Min Equity ($)
        </FormLabel>
        <NumberInput
          value={filters.min_equity ?? ''}
          min={0}
          onChange={(_valueAsString: string, valueAsNumber: number) => {
            setFilter('min_equity', Number.isNaN(valueAsNumber) ? null : valueAsNumber);
          }}
        >
          <NumberInputField placeholder="100000" />
        </NumberInput>
      </FormControl>
      <FormControl maxW="200px">
        <FormLabel fontSize="sm" color="gray.600">
          Min Score
        </FormLabel>
        <NumberInput
          value={filters.min_score ?? ''}
          min={0}
          max={100}
          onChange={(_valueAsString: string, valueAsNumber: number) => {
            setFilter('min_score', Number.isNaN(valueAsNumber) ? null : valueAsNumber);
          }}
        >
          <NumberInputField placeholder="70" />
        </NumberInput>
      </FormControl>
      <Flex justify="flex-end" gap={2}>
        <Button variant="outline" onClick={reset} colorScheme="gray">
          Reset
        </Button>
      </Flex>
    </Stack>
  );
};
