import React, { useState, useEffect } from 'react';
import { Dialog } from './Dialog';
import { Button } from './Button';
import { useTranslation } from 'react-i18next';
import { Textarea } from './Textarea';
import yaml from 'js-yaml';
import { useStore } from '../../store';
import * as Icons from 'lucide-react';
import { Checkbox } from './Checkbox';

interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PreviewItem {
  path: string;
  type: 'add' | 'update' | 'append';
  title: string;
  icon: string;
  items?: Array<{
    name: string;
    type: 'add' | 'update';
  }>;
}

export const ImportDialog: React.FC<ImportDialogProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const { configDefinition, configData, updateConfigValue } = useStore();
  const [inputText, setInputText] = useState('');
  const [format, setFormat] = useState<'json' | 'yaml'>('yaml');
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewItem[]>([]);
  const [isApplying, setIsApplying] = useState(false);
  const [overrideMode, setOverrideMode] = useState(false);

  const parseInput = (text: string): any => {
    try {
      if (format === 'json') {
        return JSON.parse(text);
      } else {
        return yaml.load(text);
      }
    } catch (error) {
      throw new Error(t('validation.invalidFormat'));
    }
  };

  const validateAgainstSchema = (path: string, value: any, schema: any) => {
    if (!schema) return true;

    if (schema.type === 'object' && typeof value !== 'object') {
      throw new Error(`${path}: Expected object`);
    }

    if (schema.required) {
      for (const required of schema.required) {
        if (!(required in value)) {
          throw new Error(`${path}: Missing required field "${required}"`);
        }
      }
    }

    if (schema.properties) {
      for (const [key, prop] of Object.entries<any>(schema.properties)) {
        if (key in value) {
          validateAgainstSchema(`${path}.${key}`, value[key], prop);
        }
      }
    }

    return true;
  };

  const generatePreview = (inputData: any) => {
    const items: PreviewItem[] = [];

    const processPath = (path: string, value: any) => {
      const configDef = configDefinition?.[path];
      if (!configDef) return;

      try {
        if (configDef.isList) {
          if (!Array.isArray(value)) {
            throw new Error(`${path}: Expected array for list configuration`);
          }

          const existingItems = !overrideMode ? path.split('.')
            .reduce((acc, part) => acc && acc[part], configData) || []
            : [];
          
          const existingNames = new Set(
            Array.isArray(existingItems) 
              ? existingItems.map(item => item.name)
              : []
          );

          const previewItem: PreviewItem = {
            path,
            type: 'append',
            title: configDef.title,
            icon: configDef.icon,
            items: value.map(item => ({
              name: item.name || t('common.unnamedInstance'),
              type: existingNames.has(item.name) && !overrideMode ? 'update' : 'add'
            }))
          };

          // Validate each item in the array
          value.forEach((item, index) => {
            validateAgainstSchema(`${path}[${index}]`, item, configDef.schema);
          });

          items.push(previewItem);
        } else {
          validateAgainstSchema(path, value, configDef.schema);
          
          const exists = path.split('.').reduce((acc, part) => acc && acc[part], configData);
          items.push({
            path,
            type: exists ? 'update' : 'add',
            title: configDef.title,
            icon: configDef.icon
          });
        }
      } catch (error) {
        throw new Error(`Validation error: ${error.message}`);
      }
    };

    for (const [key, value] of Object.entries(inputData)) {
      processPath(key, value);
    }

    return items;
  };

  useEffect(() => {
    if (!inputText.trim()) {
      setPreview([]);
      setError(null);
      return;
    }

    try {
      const parsedData = parseInput(inputText);
      const previewItems = generatePreview(parsedData);
      setPreview(previewItems);
      setError(null);
    } catch (error) {
      setError(error.message);
      setPreview([]);
    }
  }, [inputText, format, configDefinition, configData, overrideMode]);

  const handleApply = async () => {
    try {
      setIsApplying(true);
      const parsedData = parseInput(inputText);
      
      for (const [path, value] of Object.entries(parsedData)) {
        const configDef = configDefinition?.[path];
        if (!configDef) continue;

        if (configDef.isList) {
          if (overrideMode) {
            // In override mode, directly set the new value
            await updateConfigValue(path, value);
          } else {
            // Get existing items
            const currentPath = path.split('.');
            let current = configData;
            for (let i = 0; i < currentPath.length - 1; i++) {
              if (!current[currentPath[i]]) {
                current[currentPath[i]] = {};
              }
              current = current[currentPath[i]];
            }
            
            const lastKey = currentPath[currentPath.length - 1];
            const currentValue = current[lastKey] || [];
            
            // Create a map of existing items by name
            const existingItemMap = new Map(
              currentValue.map((item: any, index: number) => [item.name, index])
            );

            // Process new items
            const newValue = [...currentValue];
            for (const item of value) {
              const existingIndex = existingItemMap.get(item.name);
              if (existingIndex !== undefined) {
                // Update existing item
                newValue[existingIndex] = { ...newValue[existingIndex], ...item };
              } else {
                // Append new item
                newValue.push(item);
              }
            }

            await updateConfigValue(path, newValue);
          }
        } else {
          await updateConfigValue(path, value);
        }
      }

      onClose();
      setInputText('');
      setError(null);
    } catch (error) {
      setError(error.message);
    } finally {
      setIsApplying(false);
    }
  };

  const getIconComponent = (iconName: string) => {
    const IconComponent = (Icons as any)[iconName] || Icons.Settings;
    return <IconComponent className="h-5 w-5" />;
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={t('common.import')}
      className="w-full max-w-2xl"
    >
      <div className="mt-4 space-y-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <Button
              variant={format === 'yaml' ? 'default' : 'outline'}
              onClick={() => setFormat('yaml')}
              size="sm"
            >
              YAML
            </Button>
            <Button
              variant={format === 'json' ? 'default' : 'outline'}
              onClick={() => setFormat('json')}
              size="sm"
            >
              JSON
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="override-mode"
              checked={overrideMode}
              onChange={(e) => setOverrideMode(e.target.checked)}
            />
            <label
              htmlFor="override-mode"
              className="text-sm cursor-pointer select-none"
            >
              {t('common.completeOverride')}
            </label>
          </div>
        </div>

        <Textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={t('common.importPlaceholder')}
          className="font-mono h-48"
        />

        {error && (
          <div className="text-sm text-destructive">
            {error}
          </div>
        )}

        {preview.length > 0 && (
          <div className="border border-border rounded-md p-4 space-y-4">
            <h3 className="font-medium">{t('common.preview')}</h3>
            <div className="space-y-2">
              {preview.map((item, index) => (
                <div key={index}>
                  <div className="flex items-center gap-3 p-2 rounded-md hover:bg-muted transition-colors">
                    {getIconComponent(item.icon)}
                    <span className="font-medium">{item.title}</span>
                  </div>
                  {item.items && (
                    <div className="ml-8 space-y-1 mt-1">
                      {item.items.map((subItem, subIndex) => (
                        <div
                          key={subIndex}
                          className="flex items-center gap-2 p-2 rounded-md hover:bg-muted transition-colors text-sm"
                        >
                          <span className={subItem.type === 'add' ? 'text-success' : 'text-warning'}>
                            {subItem.type === 'add' ? '+ ' : '~ '}
                          </span>
                          <span>{subItem.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isApplying}
          >
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleApply}
            disabled={!preview.length || !!error || isApplying}
          >
            {isApplying ? t('common.applying') : t('common.apply')}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};