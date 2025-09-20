import { useState, type MouseEvent } from 'react';
import {
  Button,
  HStack,
  IconButton,
  Input,
  Menu,
  MenuButton,
  MenuDivider,
  MenuItem,
  MenuList,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import { FiFolderPlus, FiSave, FiTrash2 } from 'react-icons/fi';

import { usePropertyFilters } from '../store/filterStore';

export const FilterPresetsMenu = () => {
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { presets, savePreset, applyPreset, deletePreset } = usePropertyFilters();
  const [presetName, setPresetName] = useState('');

  const handleSave = () => {
    if (!presetName.trim()) {
      toast({ title: 'Preset name required', status: 'warning', duration: 2000 });
      return;
    }
    savePreset(presetName);
    toast({ title: 'Preset saved', description: `Stored as "${presetName.trim()}"`, status: 'success', duration: 2000 });
    setPresetName('');
    onClose();
  };

  const handleApply = (name: string) => {
    applyPreset(name);
    toast({ title: 'Preset applied', description: `Filters updated with "${name}"`, status: 'info', duration: 2000 });
  };

  const handleDelete = (event: MouseEvent<HTMLButtonElement>, name: string) => {
    event.stopPropagation();
    deletePreset(name);
    toast({ title: 'Preset removed', status: 'info', duration: 2000 });
  };

  return (
    <>
      <Menu>
        <MenuButton as={Button} leftIcon={<FiFolderPlus />} variant="outline" colorScheme="blue">
          Presets
        </MenuButton>
        <MenuList>
          <MenuItem icon={<FiSave />} onClick={onOpen}>
            Save current filters
          </MenuItem>
          <MenuDivider />
          {Object.keys(presets).length === 0 ? (
            <MenuItem isDisabled>No presets saved</MenuItem>
          ) : (
            Object.keys(presets)
              .sort((a, b) => a.localeCompare(b))
              .map((name) => (
                <MenuItem key={name} onClick={() => handleApply(name)}>
                  <HStack justify="space-between" w="full">
                    <Text>{name}</Text>
                    <IconButton
                      aria-label={`Delete preset ${name}`}
                      icon={<FiTrash2 />}
                      size="sm"
                      variant="ghost"
                      onClick={(event) => handleDelete(event, name)}
                    />
                  </HStack>
                </MenuItem>
              ))
          )}
        </MenuList>
      </Menu>

      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Save Filter Preset</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Input
              placeholder="Name this preset"
              value={presetName}
              onChange={(event) => setPresetName(event.target.value)}
            />
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button colorScheme="blue" onClick={handleSave}>
              Save Preset
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};
