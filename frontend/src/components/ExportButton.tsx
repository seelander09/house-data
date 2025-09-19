import { Button, useToast } from '@chakra-ui/react';
import { FiDownload } from 'react-icons/fi';

import { useExportProperties } from '../api/hooks';
import { usePropertyFilters } from '../store/filterStore';

export const ExportButton = () => {
  const toast = useToast();
  const { filters } = usePropertyFilters();
  const exportMutation = useExportProperties();

  const handleExport = async () => {
    try {
      await exportMutation.mutateAsync({
        ...filters,
        limit: 200,
        offset: 0,
      });
      toast({ title: 'Export in progress', description: 'CSV download started.', status: 'success', duration: 3000 });
    } catch (error) {
      toast({ title: 'Export failed', description: 'Unable to export right now. Try again shortly.', status: 'error' });
    }
  };

  return (
    <Button
      leftIcon={<FiDownload />}
      colorScheme="blue"
      variant="solid"
      onClick={handleExport}
      isLoading={exportMutation.isPending}
    >
      Export CSV
    </Button>
  );
};
