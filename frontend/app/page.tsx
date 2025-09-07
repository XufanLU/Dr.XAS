'use client'

import { ViewType } from '@/components/auth'
import { AuthDialog } from '@/components/auth-dialog'
import { Chat } from '@/components/chat'
import { ChatInput } from '@/components/chat-input'
import { ChatPicker } from '@/components/chat-picker'
import { ChatSettings } from '@/components/chat-settings'
import { NavBar } from '@/components/navbar'
import { Preview } from '@/components/preview'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'
import { Message, toAISDKMessages, toMessageImage } from '@/lib/messages'
import { LLMModelConfig } from '@/lib/models'
import modelsList from '@/lib/models.json'
// import { FragmentSchema, fragmentSchema as schema } from '@/lib/schema'
import { chatSchema } from '@/lib/chat'
import { supabase } from '@/lib/supabase'
import templates, { TemplateId } from '@/lib/templates'
import { ExecutionResult } from '@/lib/types'
import { DeepPartial } from 'ai'
import { experimental_useObject as useObject } from 'ai/react'
import { ChevronsLeft } from 'lucide-react'
import { usePostHog } from 'posthog-js/react'
import { SetStateAction, useEffect, useState } from 'react'
import { useLocalStorage } from 'usehooks-ts'
import { json } from 'stream/consumers'

export default function Home() {
  const [chatInput, setChatInput] = useLocalStorage('chat', '')
  const [files, setFiles] = useState<File[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<'auto' | TemplateId>('auto')
  const [languageModel, setLanguageModel] = useLocalStorage<LLMModelConfig>('languageModel', { model: 'claude-3-5-sonnet-latest' })
  // Add lifted state for materials and xasIDs
  const [materials, setMaterials] = useState<string[]>([])
  const [xasIDs, setXasIDs] = useState<string[]>([])
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';// todo : remove this in production

  const posthog = usePostHog()

  const [result, setResult] = useState<ExecutionResult>()
  const [messages, setMessages] = useState<Message[]>([])
  const [isPreviewVisible, setIsPreviewVisible] = useState(true)
  //const [fragment, setFragment] = useState<DeepPartial<FragmentSchema>>()
  const [currentTab, setCurrentTab] = useState<'code' | 'viz'>('viz')
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [isApiLoading, setIsApiLoading] = useState(false)
  const [isAuthDialogOpen, setAuthDialog] = useState(false)
  const [authView, setAuthView] = useState<ViewType>('sign_in')
  const [isRateLimited, setIsRateLimited] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const { session, userTeam } = useAuth(setAuthDialog, setAuthView)
  const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

  const { object, submit, isLoading, stop, error } = useObject({
  api: `${apiUrl}`,  // Your local endpoint
  schema: chatSchema, 
  onError: (error) => {
    console.error('Error submitting request:', error)
    setErrorMessage(error.message)
  },

  onFinish: async ({ object: responseObject, error }) => {
      setResult(result)
     // setCurrentPreview({ viz, result })
      setMessage({ result })
      setCurrentTab('viz')
      setIsPreviewLoading(false)
  },
}
)

  const filteredModels = modelsList.models.filter((model) => {
    if (process.env.NEXT_PUBLIC_HIDE_LOCAL_MODELS) {
      return model.providerId !== 'ollama'
    }
    return true
  })

  const currentModel = filteredModels.find(
    (model) => model.id === languageModel.model,
  )
  const currentTemplate =
    selectedTemplate === 'auto'
      ? templates
      : { [selectedTemplate]: templates[selectedTemplate] }
  const lastMessage = messages[messages.length - 1]

  // const { object, submit, isLoading, stop, error } = useObject({
  //   api: '/api/chat',
  //   schema,
  //   onError: (error) => {
  //     console.error('Error submitting request:', error)
  //     if (error.message.includes('limit')) {
  //       setIsRateLimited(true)
  //     }

  //     setErrorMessage(error.message)
  //   }
  //   // onFinish: async ({ object: fragment, error }) => {
  //   //   if (!error) {
  //   //     // send it to /api/sandbox
  //   //     console.log('fragment', fragment)
  //   //     setIsPreviewLoading(true)
  //   //     posthog.capture('fragment_generated', {
  //   //       template: fragment?.template,
  //   //     })

  //   //     const response = await fetch('/api/sandbox', {
  //   //       method: 'POST',
  //   //       body: JSON.stringify({
  //   //         fragment,
  //   //         userID: session?.user?.id,
  //   //         teamID: userTeam?.id,
  //   //         accessToken: session?.access_token,
  //   //       }),
  //   //     })

  //   //     const result = await response.json()
  //   //     console.log('result', result)
  //   //     posthog.capture('sandbox_created', { url: result.url })

  //   //     setResult(result)
  //   //     setCurrentPreview({ fragment, result })
  //   //     setMessage({ result })
  //   //     setCurrentTab('fragment')
  //   //     setIsPreviewLoading(false)
  //   //   }
  //   // },
  // })

  // useEffect(() => {
  //   if (object) {
  //     //setFragment(object)
  //     const content: Message['content'] = [
  //       { type: 'text', text: object.commentary || '' },
  //       { type: 'code', text: object.code || '' },
  //     ]

  //     if (!lastMessage || lastMessage.role !== 'assistant') {
  //       addMessage({
  //         role: 'assistant',
  //         content,
  //         object,
  //       })
  //     }

  //     if (lastMessage && lastMessage.role === 'assistant') {
  //       setMessage({
  //         content,
  //         object,
  //       })
  //     }
  //   }
  // }, [object])

  useEffect(() => {
    if (error) stop()
  }, [error, stop])

  function setMessage(message: Partial<Message>, index?: number) {
    setMessages((previousMessages) => {
      const updatedMessages = [...previousMessages]
      updatedMessages[index ?? previousMessages.length - 1] = {
        ...previousMessages[index ?? previousMessages.length - 1],
        ...message,
      }

      return updatedMessages
    })
  }

  async function handleSubmitAgent(e: React.FormEvent<HTMLFormElement>) {
  e.preventDefault()

  if (isLoading || isPreviewLoading || isApiLoading) {
    stop()
    return
  }

  // Don't proceed if no input
  if (!chatInput.trim()) {
    return
  }

  // Format the request according to your API's requirements
  const requestData = {
    conversation_id: "123", // You can make this dynamic if needed
    message: chatInput,
    materials: materials,
    xasIDs: xasIDs,
    files: await Promise.all(files.map(async (file) => {
      const content = await file.text();
      return {
        name: file.name,
        content: content,
      };
    })),
  }

  console.log('API URL:', apiUrl);
  
  // Clear any previous error messages
  setErrorMessage('')
  
  // Add the user's message immediately
  addMessage({
    role: 'user',
    content: [{ type: 'text', text: chatInput }]
  });

  // Add a loading message for the assistant
  const loadingMessage: Message = {
    role: 'assistant',
    content: [{ 
      type: 'text', 
      text: '⏳ Please wait while I process your query...' 
    }]
  };
  addMessage(loadingMessage);
  const loadingMessageIndex = messages.length + 1; // +1 because we just added the user message
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes

    // Set loading states
    setIsPreviewLoading(true)
    setIsApiLoading(true)

    const response = await fetch(`${apiUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
      signal: controller.signal,
    });
    console.log('request:', requestData);

    clearTimeout(timeoutId);

    console.log('Request data:', JSON.stringify(requestData))

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    console.log('API response:', result);

    setResult({
      sbxId: result.sbxId ?? '', // Provide a valid sbxId from the API response or fallback to empty string
      messages: result
    });
    
    // Show preview when new result arrives
    setIsPreviewVisible(true);
    
    // Update the loading message with the actual response
    setMessage({
      content: [{ type: 'text', text: result }]
    }, loadingMessageIndex);

    // Clear input and switch to viz tab
    setChatInput('');
    setCurrentTab('viz');

  } catch (error) {
    console.error('Error:', error);
    let errorMsg = 'An unexpected error occurred';
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        errorMsg = 'Request timed out. Please try again.';
      } else {
        errorMsg = error.message;
      }
    }
    
    setErrorMessage(errorMsg);
    
    // Update the loading message with error
    setMessage({
      content: [{ type: 'text', text: `Error: ${errorMsg}` }]
    }, loadingMessageIndex);
    
  } finally {
    // Always clear loading states
    setIsPreviewLoading(false)
    setIsApiLoading(false)
  }
}


  function retry() {
    submit({
      userID: session?.user?.id,
      teamID: userTeam?.id,
      messages: toAISDKMessages(messages),
      template: currentTemplate,
      model: currentModel,
      config: languageModel,
    })
  }

  function addMessage(message: Message) {
    setMessages((previousMessages) => [...previousMessages, message])
    return [...messages, message]
  }

  function handleSaveInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setChatInput(e.target.value)
  }

  function handleFileChange(change: SetStateAction<File[]>) {
    setFiles(change)
  }

  function logout() {
    supabase
      ? supabase.auth.signOut()
      : console.warn('Supabase is not initialized')
  }

  function handleLanguageModelChange(e: LLMModelConfig) {
    setLanguageModel({ ...languageModel, ...e })
  }

  function handleSocialClick(target: 'github' | 'x' | 'discord') {
    if (target === 'github') {
      window.open('https://github.com/XufanLU/Dr.XAS', '_blank')
    } else if (target === 'x') {
      window.open('https://x.com/e2b_dev', '_blank')
    } else if (target === 'discord') {
      window.open('https://discord.gg/U7KEcGErtQ', '_blank')
    }

    posthog.capture(`${target}_click`)
  }

  function handleClearChat() {
    stop()
    setChatInput('')
    setFiles([])
    setMessages([])
  //  setFragment(undefined)
    setResult(undefined)
    setCurrentTab('code')
    setIsPreviewLoading(false)
    setIsApiLoading(false)
    setIsPreviewVisible(true)
  }

  function setCurrentPreview(preview: {
    //fragment: DeepPartial<FragmentSchema> | undefined
    result: ExecutionResult | undefined
  }) {
   // setFragment(preview.fragment)
    setResult(preview.result)
  }

  function handleUndo() {
    setMessages((previousMessages) => [...previousMessages.slice(0, -2)])
    setCurrentPreview({ result: undefined })
  }

  function handleClosePreview() {
    setIsPreviewVisible(false)
  }

  function handleShowPreview() {
    setIsPreviewVisible(true)
  }


  return (
    <main className="flex min-h-screen max-h-screen relative">
      {supabase && (
        <AuthDialog
          open={isAuthDialogOpen}
          setOpen={setAuthDialog}
          view={authView}
          supabase={supabase}
        />
      )}
      
      {/* Floating Show Analysis Button */}
      {result && !isPreviewVisible && (
        <div className="fixed top-1/2 right-4 z-50 transform -translate-y-1/2">
          <Button
            onClick={handleShowPreview}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-lg rounded-full px-4 py-2"
            size="sm"
          >
            <ChevronsLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Show Report</span>
          </Button>
        </div>
      )}

      <div className="grid w-full md:grid-cols-2">
        <div
          className={`flex flex-col w-[80%] max-h-full mx-auto px-4 overflow-auto ${result && isPreviewVisible ? 'md:col-span-1' : 'md:col-span-2'}`}
        >
          <NavBar
            session={session}
            showLogin={() => setAuthDialog(true)}
            signOut={logout}
            onSocialClick={handleSocialClick}
            onClear={handleClearChat}
            canClear={messages.length > 0}
            canUndo={messages.length > 1 && !isLoading}
            onUndo={handleUndo}
          />
          {messages.length === 0 && (
            <div className="flex justify-center items-center mt-8 mb-1">
              <img src="/static/drxas_logo_big.png" alt="Dr.XAS Logo" style={{ maxWidth: '500px', width: '80%', height: 'auto' }} />
            </div>
          )}
          <Chat
            messages={messages}
            isLoading={isLoading || isApiLoading}
            setCurrentPreview={setCurrentPreview}
          />
          <div className={messages.length === 0 ? "flex flex-col flex-1" : "flex flex-col flex-1 justify-end"}>
            <div className="flex items-center justify-center w-full">
              <div className="w-[80vw] max-w-full">
                <ChatInput
                  retry={retry}
                  isErrored={error !== undefined}
                  errorMessage={errorMessage}
                  isLoading={isLoading}
                  isRateLimited={isRateLimited}
                  stop={stop}
                  input={chatInput}
                  handleInputChange={handleSaveInputChange}
                  handleSubmit={handleSubmitAgent}
                  isMultiModal={currentModel?.multiModal || false}
                  files={files}
                  handleFileChange={handleFileChange}
                  materials={materials}
                  setMaterials={setMaterials}
                  xasIDs={xasIDs}
                  setXasIDs={setXasIDs}
                >
                  {/* <ChatPicker
                    templates={templates}
                    selectedTemplate={selectedTemplate}
                    onSelectedTemplateChange={setSelectedTemplate}
                    models={filteredModels}
                    languageModel={languageModel}
                    onLanguageModelChange={handleLanguageModelChange}
                  />
                  <ChatSettings
                    languageModel={languageModel}
                    onLanguageModelChange={handleLanguageModelChange}
                    apiKeyConfigurable={!process.env.NEXT_PUBLIC_NO_API_KEY_INPUT}
                    baseURLConfigurable={!process.env.NEXT_PUBLIC_NO_BASE_URL_INPUT}
                  /> */}
                </ChatInput>
              </div>
            </div>
          </div>
        </div>
        {result && isPreviewVisible && (
          <Preview
            teamID={userTeam?.id}
            accessToken={session?.access_token}
            selectedTab={currentTab}
            onSelectedTabChange={setCurrentTab}
            isChatLoading={isLoading}
            isPreviewLoading={isPreviewLoading}
            filename={chatInput}
         //   fragment={fragment}
            result={result as ExecutionResult}
            onClose={() => handleClosePreview()}
          />
        )}
      </div>
    </main>
  )
}
