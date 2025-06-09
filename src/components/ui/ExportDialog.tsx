import React, { useState } from 'react';
import { Dialog } from './Dialog';
import { Button } from './Button';
import { useTranslation } from 'react-i18next';
import { Download, Copy, Check } from 'lucide-react';
import yaml from 'js-yaml';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  data: any;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  data
}) => {
  const { t } = useTranslation();
  const [format, setFormat] = useState<'json' | 'yaml'>('yaml');
  const [copied, setCopied] = useState(false);

  const getFormattedData = () => {
    try {
      if (format === 'json') {
        return JSON.stringify(data, null, 2);
      } else {
        return yaml.dump(data, { indent: 2 });
      }
    } catch (error) {
      console.error('Error formatting data:', error);
      return '';
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(getFormattedData());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const handleDownload = () => {
    try {
      const blob = new Blob([getFormattedData()], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `config.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download:', error);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={t('common.export')}
      className="w-full max-w-2xl"
    >
      <div className="mt-4">
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
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="flex items-center gap-2"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {t(copied ? 'common.copied' : 'common.copy')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              {t('common.download')}
            </Button>
          </div>
        </div>

        <pre className="bg-muted p-4 rounded-md overflow-auto max-h-[60vh] text-sm font-mono whitespace-pre">
          {getFormattedData()}
        </pre>

        <div className="flex justify-end mt-6">
          <Button onClick={onClose}>
            {t('common.close')}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};