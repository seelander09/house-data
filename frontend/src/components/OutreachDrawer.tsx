import { useMemo } from 'react';
import {
  Button,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  Heading,
  Stack,
  Text,
  Textarea,
  useClipboard,
  useToast,
} from '@chakra-ui/react';

import type { Property, PropertyFilters } from '../types/property';

interface OutreachDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  filters: PropertyFilters;
  properties: Property[];
}

const formatLocation = (property?: Property) =>
  property
    ? [property.city, property.state, property.postal_code].filter(Boolean).join(', ')
    : 'your target market';

const buildEmailTemplate = (property?: Property, filters?: PropertyFilters) => `Hi ${property?.owner.name ?? 'there'},

I work with homeowners in ${formatLocation(property)} who are exploring their next move. Based on public data you may have roughly $${
  property?.equity_available ? Math.round(property.equity_available).toLocaleString() : 'significant'
} in tappable equity, and properties on your block are trading well above assessed value.

Would you be open to a quick call this week to discuss a no-pressure valuation or cash buyer preview? I can share recent comps in ${
  property?.city ?? filters?.city ?? 'your area'
} and outline a timeline that works for you.

Thanks,
[Your name]
[Your phone]
`;

const buildSmsTemplate = (property?: Property, filters?: PropertyFilters) => `Hi ${property?.owner.name ?? 'there'}—this is [Your name]. I help owners in ${
  property?.city ?? filters?.city ?? 'your neighborhood'
} unlock equity. If you ever consider selling ${property?.address ?? 'your property'}, I can bring vetted buyers and quick-close options. Interested in a quick chat?`;

export const OutreachDrawer = ({ isOpen, onClose, filters, properties }: OutreachDrawerProps) => {
  const toast = useToast();
  const topProperty = properties[0];
  const emailTemplate = useMemo(() => buildEmailTemplate(topProperty, filters), [topProperty, filters]);
  const smsTemplate = useMemo(() => buildSmsTemplate(topProperty, filters), [topProperty, filters]);

  const emailClipboard = useClipboard(emailTemplate);
  const smsClipboard = useClipboard(smsTemplate);

  const handleCopy = (action: 'email' | 'sms') => {
    const clipboard = action === 'email' ? emailClipboard : smsClipboard;
    clipboard.onCopy();
    toast({ title: `${action.toUpperCase()} template copied`, status: 'success', duration: 2000 });
  };

  return (
    <Drawer isOpen={isOpen} placement="left" size="md" onClose={onClose}>
      <DrawerOverlay />
      <DrawerContent>
        <DrawerHeader borderBottomWidth="1px">Outreach Templates</DrawerHeader>
        <DrawerBody>
          <Stack spacing={6}>
            <Stack spacing={3}>
              <Heading size="sm">Email pitch</Heading>
              <Textarea value={emailTemplate} readOnly rows={12} fontFamily="mono" />
              <Button onClick={() => handleCopy('email')} colorScheme="blue" alignSelf="flex-start">
                Copy email copy
              </Button>
            </Stack>
            <Stack spacing={3}>
              <Heading size="sm">SMS opener</Heading>
              <Textarea value={smsTemplate} readOnly rows={5} fontFamily="mono" />
              <Button onClick={() => handleCopy('sms')} variant="outline" alignSelf="flex-start">
                Copy SMS copy
              </Button>
            </Stack>
            <Text fontSize="sm" color="gray.500">
              Personalise the placeholders with your branding, phone number, or investor offer before sending.
            </Text>
          </Stack>
        </DrawerBody>
        <DrawerFooter borderTopWidth="1px">
          <Button variant="outline" mr={3} onClick={onClose}>
            Close
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};
