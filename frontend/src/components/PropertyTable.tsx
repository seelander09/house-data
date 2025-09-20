import {
  Badge,
  Box,
  Button,
  ButtonGroup,
  Flex,
  HStack,
  Icon,
  IconButton,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { FiClipboard, FiHome, FiMail, FiPhone } from 'react-icons/fi';

import { usePropertyFilters } from '../store/filterStore';
import type { Property } from '../types/property';
import { ScoreBadge } from './ScoreBadge';

const columnHelper = createColumnHelper<Property>();

const columns = [
  columnHelper.accessor('address', {
    header: 'Property',
    cell: (info) => {
      const property = info.row.original;
      return (
        <Flex direction="column">
          <HStack spacing={2} align="flex-start">
            <Icon as={FiHome} color="blue.500" mt={1} />
            <Box>
              <Text fontWeight="semibold">{property.address ?? 'Address unavailable'}</Text>
              <Text fontSize="sm" color="gray.500">
                {[property.city, property.state, property.postal_code].filter(Boolean).join(', ')}
              </Text>
              <HStack spacing={2} mt={1}>
                {property.owner_occupancy && (
                  <Badge colorScheme={property.owner_occupancy === 'absentee' ? 'orange' : 'green'}>
                    {property.owner_occupancy === 'absentee' ? 'Absentee owner' : 'Owner occupied'}
                  </Badge>
                )}
                {property.distance_from_search_center_miles != null && (
                  <Badge colorScheme="purple">
                    {property.distance_from_search_center_miles.toFixed(1)} mi radius
                  </Badge>
                )}
              </HStack>
            </Box>
          </HStack>
        </Flex>
      );
    },
  }),
  columnHelper.accessor('equity_available', {
    header: 'Equity',
    cell: (info) => {
      const value = info.getValue<number | null | undefined>() ?? 0;
      return <Text>{`$${value.toLocaleString()}`}</Text>;
    },
  }),
  columnHelper.accessor('value_gap', {
    header: 'Value Gap',
    cell: (info) => {
      const value = info.getValue<number | null | undefined>();
      return <Text>{value ? `$${Math.round(value).toLocaleString()}` : '--'}</Text>;
    },
  }),
  columnHelper.accessor((row) => row.total_market_value ?? row.model_value ?? null, {
    id: 'marketValue',
    header: 'Market Value',
    cell: (info) => {
      const value = info.getValue<number | null | undefined>();
      return <Text>{value ? `$${value.toLocaleString()}` : '--'}</Text>;
    },
  }),
  columnHelper.accessor('total_assessed_value', {
    header: 'Assessed',
    cell: (info) => {
      const value = info.getValue<number | null | undefined>();
      return <Text>{value ? `$${value.toLocaleString()}` : '--'}</Text>;
    },
  }),
  columnHelper.display({
    header: 'Score',
    cell: (info) => <ScoreBadge score={info.row.original.listing_score} breakdown={info.row.original.score_breakdown} />,
  }),
  columnHelper.display({
    header: 'Owner',
    cell: (info) => {
      const owner = info.row.original.owner;
      const toast = info.table.options.meta?.toast;
      const handleLog = () => {
        toast?.({ title: 'Outreach logged', status: 'success', duration: 2000 });
      };

      return (
        <Box>
          <Text fontWeight="medium">{owner.name ?? 'Unknown'}</Text>
          <Text fontSize="sm" color="gray.500">
            {[owner.address_line1, owner.city, owner.state, owner.postal_code].filter(Boolean).join(', ')}
          </Text>
          <ButtonGroup size="sm" variant="ghost" mt={2}>
            <Tooltip label={owner.phone ? `Call ${owner.phone}` : 'No phone on file'}>
              <IconButton
                aria-label="Call owner"
                icon={<FiPhone />}
                as={owner.phone ? 'a' : 'button'}
                href={owner.phone ? `tel:${owner.phone}` : undefined}
                isDisabled={!owner.phone}
              />
            </Tooltip>
            <Tooltip label={owner.email ? `Email ${owner.email}` : 'No email on file'}>
              <IconButton
                aria-label="Email owner"
                icon={<FiMail />}
                as={owner.email ? 'a' : 'button'}
                href={owner.email ? `mailto:${owner.email}` : undefined}
                isDisabled={!owner.email}
              />
            </Tooltip>
            <Tooltip label="Log outreach touch">
              <IconButton aria-label="Log outreach" icon={<FiClipboard />} onClick={handleLog} />
            </Tooltip>
          </ButtonGroup>
        </Box>
      );
    },
  }),
];

interface PropertyTableProps {
  data: Property[];
  total: number;
  isLoading: boolean;
}

export const PropertyTable = ({ data, total, isLoading }: PropertyTableProps) => {
  const toast = useToast();
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: { toast },
  });
  const { filters, setOffset } = usePropertyFilters();
  const bg = useColorModeValue('white', 'gray.800');

  const limit = filters.limit ?? 50;
  const currentPage = Math.floor((filters.offset ?? 0) / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handlePrev = () => {
    if (currentPage <= 1) return;
    setOffset(Math.max(0, (currentPage - 2) * limit));
  };

  const handleNext = () => {
    if (currentPage >= totalPages) return;
    setOffset(currentPage * limit);
  };

  return (
    <Box bg={bg} borderRadius="lg" boxShadow="sm" overflow="hidden">
      <Table variant="simple">
        <Thead bg={useColorModeValue('gray.50', 'gray.700')}>
          {table.getHeaderGroups().map((headerGroup) => (
            <Tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Th key={header.id} fontSize="sm" textTransform="uppercase" color="gray.500">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </Th>
              ))}
            </Tr>
          ))}
        </Thead>
        <Tbody>
          {isLoading ? (
            <Tr>
              <Td colSpan={columns.length} textAlign="center" py={10}>
                <HStack justify="center" spacing={3}>
                  <Spinner size="sm" />
                  <Text color="gray.500">Loading properties...</Text>
                </HStack>
              </Td>
            </Tr>
          ) : data.length === 0 ? (
            <Tr>
              <Td colSpan={columns.length} textAlign="center" py={10}>
                <Text color="gray.500">No properties match your filters.</Text>
              </Td>
            </Tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <Tr key={row.id} _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}>
                {row.getVisibleCells().map((cell) => (
                  <Td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</Td>
                ))}
              </Tr>
            ))
          )}
        </Tbody>
      </Table>
      <Flex justify="space-between" align="center" px={6} py={4} borderTop="1px" borderColor={useColorModeValue('gray.100', 'gray.700')}>
        <Text fontSize="sm" color="gray.500">
          Showing {total === 0 ? 0 : (filters.offset ?? 0) + 1}-{Math.min((filters.offset ?? 0) + limit, total)} of {total} properties
        </Text>
        <ButtonGroup size="sm" variant="outline">
          <Button onClick={handlePrev} isDisabled={currentPage <= 1}>
            Previous
          </Button>
          <Button isDisabled>{currentPage} / {totalPages}</Button>
          <Button onClick={handleNext} isDisabled={currentPage >= totalPages}>
            Next
          </Button>
        </ButtonGroup>
      </Flex>
    </Box>
  );
};
