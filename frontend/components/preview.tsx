import { DeployDialog } from './deploy-dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { ExecutionResult } from '@/lib/types'
import { DeepPartial } from 'ai'
import { ChevronsRight, LoaderCircle, X } from 'lucide-react'
import { Dispatch, SetStateAction, useState, useEffect } from 'react'
import { S3Client , GetObjectCommand} from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import Image from 'next/image';

export function Preview({
  teamID,
  accessToken,
  selectedTab,
  onSelectedTabChange,
  isChatLoading,
  isPreviewLoading,
  filename,
  result,
  onClose,
}: {
  teamID: string | undefined
  accessToken: string | undefined
  selectedTab: 'code' | 'viz'
  onSelectedTabChange: Dispatch<SetStateAction<'code' | 'viz'>>
  isChatLoading: boolean
  isPreviewLoading: boolean
  filename: string
  result?: ExecutionResult
  onClose: () => void
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('Fetching image from S3...');
    const downloadFromS3 = async () => {
    const accessKeyId = process.env.NEXT_PUBLIC_AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY;
    
    if (!accessKeyId || !secretAccessKey) {
      setError('AWS credentials not configured');
      setLoading(false);
      return;
    }

    const s3Client = new S3Client({
      credentials: {
        accessKeyId,
        secretAccessKey,
      },
      region: "eu-north-1"
    });
      setLoading(true);
      const command = new GetObjectCommand({
        Bucket: 'test-dr-xas',
        Key: 'viz/Ni_foil_all.jpg', // Adjust the key based on your S3 structure
      });


    try {
    
      const url = await getSignedUrl(s3Client, command, { expiresIn: 3600 });
      setImageUrl(url);
      setLoading(false);
     
      
    } catch (err) {
      console.error('Error downloading file:', err);
      setError(err instanceof Error ? err.message : 'Failed to load image');
      setLoading(false);
    }
    };

    downloadFromS3();

    // Cleanup function
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]); // Include imageUrl in dependency array

  return (
  <div className="absolute md:relative z-10 top-0 left-0 shadow-2xl md:rounded-tl-3xl md:rounded-bl-3xl md:border-l md:border-y bg-popover h-full w-full min-w-0 max-w-none overflow-auto">
      <Tabs
        value={selectedTab}
        onValueChange={(value) =>
          onSelectedTabChange(value as 'code' | 'viz')
        }
        className="h-full flex flex-col w-full"
      >
        <div className="w-full p-2 grid grid-cols-3 items-center border-b">
          <TooltipProvider>
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="w-8 h-8 p-0"
                >
                  <ChevronsRight className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Collapse preview</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <div className=" flex justify-center items-center">
            <p className="text-center font-semibold">Report</p>
          </div>
        </div>
        <TabsContent value={selectedTab} className="w-full flex-1">
  {result && (
  <div className="p-4 space-y-4 w-full">
      {/* 1. XAS Spectra Viewer Section */}
  <details className="border rounded w-full min-w-0" open>
        <summary className="cursor-pointer font-semibold p-2">1. XAS Spectra Viewer</summary>
        <div className="p-2">
          {/* TODO: Insert XAS spectra viewer component or placeholder */}
          <div className="text-gray-500">[XAS Spectra Viewer goes here]</div>
        </div>
      </details>

      {/* 2. CIF Viewer Section */}
  <details className="border rounded w-full min-w-0" open>
        <summary className="cursor-pointer font-semibold p-2">2. CIF Viewer</summary>
        <div className="p-2">
          {/* TODO: Insert CIF viewer component or placeholder */}
          <div className="text-gray-500">[CIF Viewer goes here]</div>
        </div>
      </details>

      {/* 3. Figure Section */}
  <details className="border rounded w-full min-w-0" open>
        <summary className="cursor-pointer font-semibold p-2">3. Figure</summary>
        <div className="relative w-full h-[400px] p-2">
          {loading && <div>Loading image...</div>}
          {error && <div className="text-red-500">Error: {error}</div>}
          {imageUrl && !loading && (
            <Image
              src={imageUrl}
              alt="XAS Analysis"
              fill
              style={{ objectFit: 'contain' }}
              onError={(e) => {
                console.error('Image loading error:', e);
                setError('Failed to load image');
              }}
              unoptimized
              priority
            />
          )}
        </div>
      </details>

      {/* 4. Result Messages as Table Section */}
  <details className="border rounded w-full min-w-0" open>
        <summary className="cursor-pointer font-semibold p-2">4. Result Table</summary>
        <div className="p-2 overflow-x-auto">
          {Array.isArray(result.messages) ? (
            <table className="min-w-full text-sm border">
              <tbody>
                {result.messages.map((row: any, i: number) => (
                  <tr key={i} className="border-b">
                    {Array.isArray(row) ? row.map((cell, j) => (
                      <td key={j} className="px-2 py-1 border-r">{cell}</td>
                    )) : <td className="px-2 py-1">{row}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <pre className="max-w-[100%] whitespace-pre-wrap break-words">{result.messages}</pre>
          )}
        </div>
      </details>
    </div>
  )}
</TabsContent>
      </Tabs>
    </div>
  );
}