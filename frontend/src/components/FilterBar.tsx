import type { ChangeEvent } from 'react';
import {
  Button,
  Collapse,
  Flex,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  Input,
  NumberInput,
  NumberInputField,
  Select,
  Stack,
  Tooltip,
  useBoolean,
} from '@chakra-ui/react';
import { FiSliders } from 'react-icons/fi';

import { FilterPresetsMenu } from './FilterPresetsMenu';
import { usePropertyFilters } from '../store/filterStore';

type TextFilterKey = 'search' | 'city' | 'state' | 'postal_code' | 'owner_occupancy';
type NumericFilterKey =
  | 'min_equity'
  | 'min_score'
  | 'min_value_gap'
  | 'min_market_value'
  | 'max_market_value'
  | 'min_assessed_value'
  | 'max_assessed_value'
  | 'center_latitude'
  | 'center_longitude'
  | 'radius_miles';

export const FilterBar = () => {
  const { filters, setFilter, reset } = usePropertyFilters();
  const [advancedVisible, setAdvancedVisible] = useBoolean(false);

  const handleText = (key: TextFilterKey) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFilter(key, event.target.value);
  };

  const handleNumber = (key: NumericFilterKey) => (_valueAsString: string, valueAsNumber: number) => {
    setFilter(key, Number.isNaN(valueAsNumber) ? null : valueAsNumber);
  };

  return (
    <Stack spacing={4} w="full" bg="white" p={4} borderRadius="lg" boxShadow="sm">
      <Stack direction={{ base: 'column', xl: 'row' }} spacing={4} align={{ base: 'stretch', xl: 'flex-end' }}>
        <FormControl maxW="260px">
          <FormLabel fontSize="sm" color="gray.600">
            Search
          </FormLabel>
          <Input value={filters.search ?? ''} onChange={handleText('search')} placeholder="Address, owner, parcel" />
        </FormControl>
        <FormControl maxW="200px">
          <FormLabel fontSize="sm" color="gray.600">
            City
          </FormLabel>
          <Input value={filters.city ?? ''} onChange={handleText('city')} placeholder="City" />
        </FormControl>
        <FormControl maxW="120px">
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
          <NumberInput value={filters.min_equity ?? ''} min={0} onChange={handleNumber('min_equity')}>
            <NumberInputField placeholder="100000" />
          </NumberInput>
        </FormControl>
        <FormControl maxW="160px">
          <FormLabel fontSize="sm" color="gray.600">
            Min Score
          </FormLabel>
          <NumberInput value={filters.min_score ?? ''} min={0} max={100} onChange={handleNumber('min_score')}>
            <NumberInputField placeholder="70" />
          </NumberInput>
        </FormControl>
        <FormControl maxW="200px">
          <FormLabel fontSize="sm" color="gray.600">
            Owner Type
          </FormLabel>
          <Select value={filters.owner_occupancy ?? ''} onChange={handleText('owner_occupancy')}>
            <option value="">All owners</option>
            <option value="owner_occupied">Owner occupied</option>
            <option value="absentee">Absentee / investor</option>
          </Select>
        </FormControl>
        <Flex gap={2} justify={{ base: 'flex-start', xl: 'flex-end' }} align="center">
          <FilterPresetsMenu />
          <Tooltip label={advancedVisible ? 'Hide advanced filters' : 'Show advanced filters'}>
            <IconButton
              aria-label="Toggle advanced filters"
              icon={<FiSliders />}
              variant="outline"
              onClick={setAdvancedVisible.toggle}
            />
          </Tooltip>
          <Button variant="outline" onClick={reset} colorScheme="gray">
            Reset
          </Button>
        </Flex>
      </Stack>

      <Collapse in={advancedVisible} animateOpacity>
        <Stack direction={{ base: 'column', xl: 'row' }} spacing={4} mt={2} align={{ base: 'stretch', xl: 'flex-end' }}>
          <FormControl maxW="160px">
            <FormLabel fontSize="sm" color="gray.600">
              Postal Code
            </FormLabel>
            <Input value={filters.postal_code ?? ''} onChange={handleText('postal_code')} placeholder="Zip or prefix" />
          </FormControl>
          <FormControl maxW="180px">
            <FormLabel fontSize="sm" color="gray.600">
              Min Value Gap ($)
            </FormLabel>
            <NumberInput value={filters.min_value_gap ?? ''} min={0} onChange={handleNumber('min_value_gap')}>
              <NumberInputField placeholder="50000" />
            </NumberInput>
          </FormControl>
          <HStack spacing={4} align="flex-end">
            <FormControl maxW="180px">
              <FormLabel fontSize="sm" color="gray.600">
                Min Market Value
              </FormLabel>
              <NumberInput value={filters.min_market_value ?? ''} min={0} onChange={handleNumber('min_market_value')}>
                <NumberInputField placeholder="250000" />
              </NumberInput>
            </FormControl>
            <FormControl maxW="180px">
              <FormLabel fontSize="sm" color="gray.600">
                Max Market Value
              </FormLabel>
              <NumberInput value={filters.max_market_value ?? ''} min={0} onChange={handleNumber('max_market_value')}>
                <NumberInputField placeholder="750000" />
              </NumberInput>
            </FormControl>
          </HStack>
          <HStack spacing={4} align="flex-end">
            <FormControl maxW="180px">
              <FormLabel fontSize="sm" color="gray.600">
                Min Assessed Value
              </FormLabel>
              <NumberInput value={filters.min_assessed_value ?? ''} min={0} onChange={handleNumber('min_assessed_value')}>
                <NumberInputField placeholder="200000" />
              </NumberInput>
            </FormControl>
            <FormControl maxW="180px">
              <FormLabel fontSize="sm" color="gray.600">
                Max Assessed Value
              </FormLabel>
              <NumberInput value={filters.max_assessed_value ?? ''} min={0} onChange={handleNumber('max_assessed_value')}>
                <NumberInputField placeholder="600000" />
              </NumberInput>
            </FormControl>
          </HStack>
          <HStack spacing={4} align="flex-end">
            <FormControl maxW="200px">
              <FormLabel fontSize="sm" color="gray.600">
                Center Latitude
              </FormLabel>
              <NumberInput
                value={filters.center_latitude ?? ''}
                onChange={handleNumber('center_latitude')}
                step={0.0001}
              >
                <NumberInputField placeholder="30.2672" />
              </NumberInput>
            </FormControl>
            <FormControl maxW="200px">
              <FormLabel fontSize="sm" color="gray.600">
                Center Longitude
              </FormLabel>
              <NumberInput
                value={filters.center_longitude ?? ''}
                onChange={handleNumber('center_longitude')}
                step={0.0001}
              >
                <NumberInputField placeholder="-97.7431" />
              </NumberInput>
            </FormControl>
            <FormControl maxW="160px">
              <FormLabel fontSize="sm" color="gray.600">
                Radius (mi)
              </FormLabel>
              <NumberInput value={filters.radius_miles ?? ''} min={0} step={0.5} onChange={handleNumber('radius_miles')}>
                <NumberInputField placeholder="5" />
              </NumberInput>
            </FormControl>
          </HStack>
        </Stack>
      </Collapse>
    </Stack>
  );
};
