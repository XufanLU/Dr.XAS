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





















  // Use structured fields if available
  // Allow extra fields on result for new API structure
  const extendedResult = result as ExecutionResult & {
    material_url?: string;
    xas_url?: string;
    fitting_result_url?: string;
    message?: string;
  };
  const materialUrl = extendedResult && typeof extendedResult.material_url === 'string' ? extendedResult.material_url : '';
  const xasUrl = extendedResult && typeof extendedResult.xas_url === 'string' ? extendedResult.xas_url : '';
  const fittingUrl = extendedResult && typeof extendedResult.fitting_result_url === 'string' ? extendedResult.fitting_result_url : '';
  const mainMessage = extendedResult && typeof extendedResult.message === 'string' ? extendedResult.message : '';

  // Download XAS file from S3 using xasUrl and show as PNG image by default
  const [xasDownloadUrl, setXasDownloadUrl] = useState<string | null>(null);
  const [imgScale, setImgScale] = useState<number>(1);
  const [imgOffset, setImgOffset] = useState<{x: number, y: number}>({x: 0, y: 0});
  const [dragging, setDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{x: number, y: number} | null>(null);

  // CIF viewer state
  const [cifContent, setCifContent] = useState<string | null>(null);
  const [cifScale, setCifScale] = useState<number>(1);
  const [cifOffset, setCifOffset] = useState<{x: number, y: number}>({x: 0, y: 0});
  const [cifDragging, setCifDragging] = useState<boolean>(false);
  const [cifDragStart, setCifDragStart] = useState<{x: number, y: number} | null>(null);

  useEffect(() => {
    const fetchXasUrl = async () => {
      if (!xasUrl) return;
      const accessKeyId = process.env.NEXT_PUBLIC_AWS_ACCESS_KEY_ID;
      const secretAccessKey = process.env.NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY;
      if (!accessKeyId || !secretAccessKey) {
        setError('AWS credentials not configured');
        return;
      }
      const s3Client = new S3Client({
        credentials: { accessKeyId, secretAccessKey },
        region: "eu-north-1"
      });
      const command = new GetObjectCommand({
        Bucket: 'test-dr-xas',
        Key: xasUrl, // Use xasUrl as the S3 key
      });
      try {
        const url = await getSignedUrl(s3Client, command, { expiresIn: 3600 });
        setXasDownloadUrl(url);
      } catch (err) {
        setError('Failed to get XAS file URL');
      }
    };
    fetchXasUrl();
  }, [xasUrl]);

  useEffect(() => {
    const fetchCif = async () => {
      if (!materialUrl) return;
      try {
        // If materialUrl is a presigned URL, just fetch it. If it's a key, generate signed URL (like xasUrl logic)
        let url = materialUrl;
        if (!/^https?:\/\//.test(materialUrl)) {
          const accessKeyId = process.env.NEXT_PUBLIC_AWS_ACCESS_KEY_ID;
          const secretAccessKey = process.env.NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY;
          if (!accessKeyId || !secretAccessKey) {
            setError('AWS credentials not configured');
            return;
          }
          const s3Client = new S3Client({
            credentials: { accessKeyId, secretAccessKey },
            region: "eu-north-1"
          });
          const command = new GetObjectCommand({
            Bucket: 'test-dr-xas',
            Key: materialUrl,
          });
          url = await getSignedUrl(s3Client, command, { expiresIn: 3600 });
        }
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('Failed to fetch CIF file');
        const text = await resp.text();
        setCifContent(text);
      } catch (err) {
        setError('Failed to load CIF file');
      }
    };
    fetchCif();
  }, [materialUrl]);


useEffect(() => {
  if (cifContent && typeof window !== 'undefined') {
    import('3dmol').then(($3Dmol) => {
      const element = document.getElementById("cif-viewer");
      if (element) {
        const config = { backgroundColor: 'white' };
        const viewer = $3Dmol.createViewer(element, config);
        viewer.addModel(cifContent, "cif");
        viewer.setStyle({}, { stick: { radius: 0.15 }, sphere: { scale: 0.3 } });
        viewer.zoomTo();
        viewer.render();
      }
    });
  }
}, [cifContent]);



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
                  {xasDownloadUrl ? (
                    <>
                      {/* <a href={xasDownloadUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">Download XAS Data from S3</a> */}
                      <div
                        className="relative mt-2 border rounded shadow bg-white select-none"
                        style={{height: '400px', width: '100%', minHeight: '100px', overflow: 'hidden', cursor: dragging ? 'grabbing' : 'grab'}}
                        onMouseDown={e => {
                          setDragging(true);
                          setDragStart({x: e.clientX - imgOffset.x, y: e.clientY - imgOffset.y});
                        }}
                        onMouseUp={() => setDragging(false)}
                        onMouseLeave={() => setDragging(false)}
                        onMouseMove={e => {
                          if (dragging && dragStart) {
                            setImgOffset({
                              x: e.clientX - dragStart.x,
                              y: e.clientY - dragStart.y
                            });
                          }
                        }}
                      >
                        {/* Zoom controls in top-right corner */}
                        <div className="absolute top-2 right-2 flex items-center gap-2 z-10 bg-white/80 p-1 rounded shadow">
                          <button
                            type="button"
                            className="px-2 py-1 bg-gray-200 rounded hover:bg-gray-300 border"
                            onClick={e => { e.stopPropagation(); setImgScale((s) => Math.min(s + 0.2, 5)); }}
                            aria-label="Zoom in"
                          >
                            +
                          </button>
                          <button
                            type="button"
                            className="px-2 py-1 bg-gray-200 rounded hover:bg-gray-300 border"
                            onClick={e => { e.stopPropagation(); setImgScale((s) => Math.max(s - 0.2, 0.2)); }}
                            aria-label="Zoom out"
                          >
                            -
                          </button>
                          <span className="text-xs text-gray-500">{(imgScale * 100).toFixed(0)}%</span>
                        </div>
                        <img
                          src={xasDownloadUrl}
                          alt="XAS PNG"
                          draggable={false}
                          style={{
                            transform: `translate(${imgOffset.x}px, ${imgOffset.y}px) scale(${imgScale})`,
                            transformOrigin: 'top left',
                            transition: dragging ? 'none' : 'transform 0.2s',
                            userSelect: 'none',
                            pointerEvents: 'auto',
                          }}
                          className="block max-w-none"
                        />
                      </div>
                    </>
                  ) : xasUrl ? (
                    <div className="text-gray-500">Generating download link...</div>
                  ) : (
                    <div className="text-gray-500">[XAS Spectra Viewer goes here]</div>
                  )}
                </div>
              </details>

              {/* 2. CIF Viewer Section */}
              <details className="border rounded w-full min-w-0" open>
                <summary className="cursor-pointer font-semibold p-2">2. CIF Viewer</summary>
                <div className="p-2">
                  {materialUrl ? (
                    <>
                      <div
                        className="relative border rounded shadow bg-white select-none"
                        style={{ height: '400px', width: '100%', minHeight: '100px' }}
                      >
                        <div
                          id="cif-viewer"
                          style={{ width: '100%', height: '100%' }}
                        />
                      </div>
                    </>
                  ) : (
                    <div className="text-gray-500">[CIF Viewer goes here]</div>
                  )}
                </div>
              </details>


              {/* 4. Result Messages as Table Section */}
              <details className="border rounded w-full min-w-0" open>
                <summary className="cursor-pointer font-semibold p-2">4. Result Table</summary>
                <div className="p-2 overflow-x-auto">
                  {mainMessage && (
                    <div className="mb-2 font-semibold">{mainMessage}</div>
                  )}
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