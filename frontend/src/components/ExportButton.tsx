import { Button, useToast } from '@chakra-ui/react';
import { isAxiosError } from 'axios';
import { FiDownload } from 'react-icons/fi';

import { useExportProperties, usePlanSnapshotQuery } from '../api/hooks';
import { usePropertyFilters } from '../store/filterStore';

export const ExportButton = () => {
  const toast = useToast();
  const { filters } = usePropertyFilters();
  const exportMutation = useExportProperties();
  const { data: planSnapshot } = usePlanSnapshotQuery();

  const exportQuota = planSnapshot?.quotas.find((quota) => quota.event_type === 'properties.export');
  const exportLimitReached = (exportQuota?.remaining ?? 1) <= 0;

  const handleExport = async () => {
    try {
      const count = await exportMutation.mutateAsync({
        ...filters,
        limit: 500,
        offset: 0,
      });
      toast({
        title: 'Export in progress',
        description: count ? `${count} properties queued in your CSV download.` : 'CSV download started.',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      let description = 'Unable to export right now. Try again shortly.';
      if (isAxiosError(error) && error.response?.status === 429) {
        const detail = (error.response.data as { detail?: string })?.detail;
        description = detail ?? 'Plan usage limit reached for exports.';
      }
      toast({ title: 'Export failed', description, status: 'error', duration: 4000 });
    }
  };

  return (
    <Button
      leftIcon={<FiDownload />}
      colorScheme="blue"
      variant="solid"
      onClick={handleExport}
      isLoading={exportMutation.isPending}
      isDisabled={exportLimitReached}
      title={exportLimitReached ? 'Export quota reached for your plan' : undefined}
    >
      Export CSV
    </Button>
  );
};
