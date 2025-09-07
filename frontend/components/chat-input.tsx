'use client'

import { RepoBanner } from './repo-banner'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { isFileInArray } from '@/lib/utils'
import { ArrowUp, Paperclip, Plus, Square, X } from 'lucide-react'
import { SetStateAction, use, useEffect, useMemo, useState } from 'react'
import TextareaAutosize from 'react-textarea-autosize'
import { DataBasePicker} from './database-picker'
import { MaterialSpecimenPicker, MaterialSpecimenMap } from './material-specimen-picker'
import databases,{ Databases } from '@/lib/database'
import { NodeNextRequest } from 'next/dist/server/base-http/node'

export function ChatInput({
  retry,
  isErrored,
  errorMessage,
  isLoading,
  isRateLimited,
  stop,
  input,
  handleInputChange,
  handleSubmit,
  isMultiModal,
  files,
  handleFileChange,
  materials,
  setMaterials,
  xasIDs,
  setXasIDs,
  children,
}: {
  retry: () => void
  isErrored: boolean
  errorMessage: string
  isLoading: boolean
  isRateLimited: boolean
  stop: () => void
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  isMultiModal: boolean
  files: File[]
  handleFileChange: (change: SetStateAction<File[]>) => void
  materials: string[]
  setMaterials: React.Dispatch<React.SetStateAction<string[]>>
  xasIDs: string[]
  setXasIDs: React.Dispatch<React.SetStateAction<string[]>>
  children?: React.ReactNode
}) {
  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    handleFileChange((prev) => {
      const newFiles = Array.from(e.target.files || [])
      const uniqueFiles = newFiles.filter((file) => !isFileInArray(file, prev))
      return [...prev, ...uniqueFiles]
    })
  }

  function handleFileRemove(file: File) {
    handleFileChange((prev) => prev.filter((f) => f !== file))
    if (file.name in materialSpecimenMap
      && materialSpecimenMap[file.name][0]  // check if the file name corresponds to a material with an XASID
      && materialSpecimenMap[file.name][0] in xasIDs) // check if the XASID is in the current list
      setXasIDs((prev) => [...prev, materialSpecimenMap[file.name][0]])


    // Remove the material (chemical formula) if the file name matches a material in the materials array
    setMaterials((prev) => prev.filter((mat) => mat !== file.name.replace(/\.cif$/i, '')))
    // If the removed file is an XASID file, clear xasIDs if it matches
    setXasIDs((prev) => prev.filter((id) => id !== materialSpecimenMap[file.name][0]))

  }
  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = Array.from(e.clipboardData.items)

    for (const item of items) {
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault()

        const file = item.getAsFile()
        if (file) {
          handleFileChange((prev) => {
            if (!isFileInArray(file, prev)) {
              return [...prev, file]
            }
            return prev
          })
        }
      }
    }
  }

  const [dragActive, setDragActive] = useState(false)
  const [databasesState, setDatabasesState] = useState<Databases>(databases)
  const [selectedDatabase, setSelectedDatabase] = useState<'auto' | keyof Databases>('auto')
  const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

  // Fetch material/specimen map from API
  const [materialSpecimenMap, setMaterialSpecimenMap] = useState<MaterialSpecimenMap>({})
  const [chemicalFormula, setChemicalFormula] = useState<string>('')
  // xasIDs and materials are now lifted to parent



  useEffect(() => {
    async function fetchMaterialSpecimenMap() {
      try {

        const res = await fetch(`${apiUrl}/xafs_database`)
        if (!res.ok) throw new Error('Failed to fetch material database')
        const data = await res.json()
        // Expecting data in the format: { [materialId]: [specimen, ...] }
        setMaterialSpecimenMap(data)
      } catch (err) {
        // Optionally handle error, e.g. show a message
        setMaterialSpecimenMap({})
      }
    }
    fetchMaterialSpecimenMap()
  }, [])
  const [selectedMaterial, setSelectedMaterial] = useState<string>('')

  // Fetch chemical formula for a material
  async function fetchChemicalFormula(materialName: string) {
    try {
      const res = await fetch(`${apiUrl}/chemical_formula/${encodeURIComponent(materialName)}`)
      if (!res.ok) throw new Error('Failed to fetch chemical formula')
      const data = await res.json()
      setChemicalFormula(data)
    } catch (err) {
      setChemicalFormula('')
    }
  }

  // Update chemical formula when selectedMaterial changes
  useEffect(() => {
    if (selectedMaterial) {
      fetchChemicalFormula(selectedMaterial)
    } else {
      setChemicalFormula('')
    }
  }, [selectedMaterial])




  function handleDrag(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFiles = Array.from(e.dataTransfer.files).filter((file) =>
      file.type.startsWith('image/'),
    )

    if (droppedFiles.length > 0) {
      handleFileChange((prev) => {
        const uniqueFiles = droppedFiles.filter(
          (file) => !isFileInArray(file, prev),
        )
        return [...prev, ...uniqueFiles]
      })
    }
  }

  const filePreview = useMemo(() => {
    if (files.length === 0) return null
    return Array.from(files).map((file) => {
      const isImage = file.type.startsWith('image/')
      return (
        <div className="relative flex items-center gap-2" key={file.name}>
          <span
            onClick={() => handleFileRemove(file)}
            className="absolute top-[-8] right-[-8] bg-muted rounded-full p-1"
          >
            <X className="h-3 w-3 cursor-pointer" />
          </span>
          {isImage ? (
            <img
              src={URL.createObjectURL(file)}
              alt={file.name}
              className="rounded-xl w-10 h-10 object-cover"
            />
          ) : (
            <span className="rounded-xl border px-2 py-1 text-xs bg-muted text-muted-foreground">{file.name}</span>
          )}
        </div>
      )
    })
  }, [files])

  function onEnter(e: React.KeyboardEvent<HTMLFormElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      if (e.currentTarget.checkValidity()) {
        handleSubmit(e)
      } else {
        e.currentTarget.reportValidity()
      }
    }
  }

  useEffect(() => {
    if (!isMultiModal) {
      handleFileChange([])
    }
  }, [isMultiModal])


 function onSelectedDatabaseChange(database: 'auto' | keyof Databases) {
    setSelectedDatabase(database)
  }

  function onMaterialChange(xasTitle: string) {
    // The map is { [materialId]: [xasId, materialName] }
    const dataInfo = materialSpecimenMap[xasTitle] || []
    const XASID= dataInfo[0] || ''
    setSelectedMaterial(xasTitle)

    // Set XAS IDs (here, just the xasId as an array for consistency)
    setXasIDs(prev => [...prev, XASID])

    console.log("Selected material:", xasTitle, "XAS IDs:", XASID ? [XASID] : [])

    fetchChemicalFormula(xasTitle)
    console.log("Current XASIDs:", xasIDs)


    // when I delete the file, also delete the XASID from the XASIS list . 
  

    // Extract file name from path

    // filePath is the file path, fetch it and add as a File to files
    fetch(`${apiUrl}/xafs/${XASID}`)
      .then((res) => res.blob())
      .then((blob) => { 
        const file = new File([blob], xasTitle, { type: blob.type || 'application/octet-stream' })
        handleFileChange((prev) => {
          if (!isFileInArray(file, prev)) {
            return [...prev, file]
          }
          return prev 
        })
      })
      .catch((err) => {
        console.error('Error fetching XAFS data:', err)
      })
  }
  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={onEnter}
      className="mb-2 mt-auto flex flex-col bg-background"
      onDragEnter={isMultiModal ? handleDrag : undefined}
      onDragLeave={isMultiModal ? handleDrag : undefined}
      onDragOver={isMultiModal ? handleDrag : undefined}
      onDrop={isMultiModal ? handleDrop : undefined}
    >
      {isErrored && (
        <div
          className={`flex items-center p-1.5 text-sm font-medium mx-4 mb-10 rounded-xl ${
            isRateLimited
              ? 'bg-orange-400/10 text-orange-400'
              : 'bg-red-400/10 text-red-400'
          }`}
        >
          <span className="flex-1 px-1.5">{errorMessage}</span>
          <button
            className={`px-2 py-1 rounded-sm ${
              isRateLimited ? 'bg-orange-400/20' : 'bg-red-400/20'
            }`}
            onClick={retry}
          >
            Try again
          </button>
        </div>
      )}
      <div className="relative">
        <RepoBanner className="absolute bottom-full inset-x-2 translate-y-1 z-0 pb-2" />
        <div
          className={`shadow-md rounded-2xl relative z-10 bg-background border ${
            dragActive
              ? 'before:absolute before:inset-0 before:rounded-2xl before:border-2 before:border-dashed before:border-primary'
              : ''
          }`}
        >
          <div className="flex items-center px-3 py-2 gap-1">{children}</div>
          <TextareaAutosize
            autoFocus={true}
            minRows={1}
            maxRows={5}
            className="text-normal px-3 resize-none ring-0 bg-inherit w-full m-0 outline-none"
            required={true}
            //placeholder="Ni_foil"
            placeholder="Try a random material's fit pulled from the MDR XAFS database"
            disabled={isErrored}
            value={input}
            onChange={handleInputChange}
            onPaste={isMultiModal ? handlePaste : undefined}
          />
            <div className="flex p-3 gap-2 items-center">
            <input
              type="file"
              id="multimodal"
              name="multimodal"
              accept="image/*,.txt"
              multiple={true}
              className="hidden"
              onChange={handleFileInput}
            />

            <div className="flex items-center flex-1 gap-2">
              <TooltipProvider>
                {/* Spectrum upload button */}
                <Tooltip delayDuration={0}>
                  <TooltipTrigger asChild>
                    <Button
                      disabled={!isMultiModal || isErrored}
                      type="button"
                      variant="outline"
                      size="icon"
                      className="rounded-xl h-10 min-w-[140px] px-3 flex flex-row items-center justify-between"
                      onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('multimodal')?.click()
                      }}
                    >
                      <p style={{ fontSize: '0.75rem', marginRight: '4px' }}>upload spectrum</p>
                      <Plus className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  {/* <TooltipContent>upload spectrum from local</TooltipContent> */}
                </Tooltip>

                
                <MaterialSpecimenPicker
                  materialSpecimenMap={materialSpecimenMap}
                  selectedMaterial={selectedMaterial}
                  onMaterialChange={onMaterialChange}
                />
              </TooltipProvider>
              {files.length > 0 && filePreview}
            </div>
            <TooltipProvider>
              {/* cif upload button for material database */}
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <Button
                    disabled={!isMultiModal || isErrored}
                      type="button"
                      variant="outline"
                      size="icon"
                      className="rounded-xl h-10 min-w-[140px] px-3 flex flex-row items-center justify-between"
                      onClick={(e) => {
                        e.preventDefault()
                        document.getElementById('cif-upload')?.click()
                      }}
                    >
                      <p style={{ fontSize: '0.75rem', marginRight: '4px' }}>upload cif</p>
                     <Plus className="h-3 w-3" />
                    </Button>
                  </TooltipTrigger>
                  {/* <TooltipContent>upload cif</TooltipContent> */}
                </Tooltip>
                {/* Hidden cif file input */}
                <input
                  type="file"
                  id="cif-upload"
                  name="cif-upload"
                  accept=".cif"
                  multiple={false}
                  className="hidden"
                  onChange={(e) => {
                    const cifFile = e.target.files?.[0]
                    if (cifFile) {
                      handleFileChange((prev) => {
                        if (!isFileInArray(cifFile, prev)) {
                          return [...prev, cifFile]
                        }
                        return prev
                      })
                    }
                  }}
                />
   

            <div className="relative min-w-[120px]">
              <input
                type="text"
                value={chemicalFormula}
                onChange={e => setChemicalFormula(e.target.value)}
                placeholder="search cif by formula"
                className="border rounded pr-10 pl-2 py-1 text-sm w-full bg-gray-100"
              />
              <button
                type="button"
                aria-label="search cif by formula"
                className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-gray-200 focus:outline-none"
                style={{ height: '1.75rem', width: '1.75rem' }}
                onClick={async () => {
                  if (!chemicalFormula) return;
                  try {
                    const res = await fetch(`${apiUrl}/material_database/${encodeURIComponent(chemicalFormula)}`);
                    if (!res.ok) throw new Error('No CIF found');
                    const blob = await res.blob();
                    const file = new File([blob], `${chemicalFormula}.cif`, { type: blob.type || 'application/octet-stream' });
                    handleFileChange((prev) => {
                      if (!isFileInArray(file, prev)) {
                        // Add file and also add chemicalFormula to materials if not already present
                       
                        console.log("Materials after adding:", materials);
                        return [...prev, file];
                      }
                      return prev;
                    });
                     setMaterials((mats) => mats.includes(chemicalFormula) ? mats : [...mats, chemicalFormula]);
                  } catch (err) {
                    alert('CIF file not found for this formula. Please upload manually.');
                  }
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-500">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z" />
                </svg>
              </button>
            </div>

              {/* <DataBasePicker
              databases={databasesState}
              selectedDatabase={selectedDatabase}
              onSelectedDatabaseChange={onSelectedDatabaseChange}
            /> */}
   </TooltipProvider>
            <div>
              {!isLoading ? (
              <TooltipProvider>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                  <Button
                  disabled={isErrored}
                  variant="default"
                  size="icon"
                  type="submit"
                  className="rounded-xl h-10 w-10"
                  >
                  <ArrowUp className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Send message</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              ) : (
              <TooltipProvider>
                <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <Button
                  variant="secondary"
                  size="icon"
                  className="rounded-xl h-10 w-10"
                  onClick={(e) => {
                    e.preventDefault()
                    stop()
                  }}
                  >
                  <Square className="h-5 w-5" />
                  </Button>
                    </TooltipTrigger>
                    <TooltipContent>Stop generation</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>
        </div>
      </div>
    </form>
  )
}
