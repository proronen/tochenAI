import { useState } from 'react';
import {
  Box,
  Text,
  Textarea,
  Button,
  VStack,
  HStack,
  Badge,
} from '@chakra-ui/react';
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogCloseTrigger,
} from '../ui/dialog';
import { Field } from '../ui/field';
import { generatePostIdeas } from '../../client/core/request';
import useAuth from '../../hooks/useAuth';
import PostContentModal from './PostContentModal';
import useCustomToast from '../../hooks/useCustomToast';

interface PostIdeasModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPostCreated: () => void;
}

interface PostIdea {
  id: string;
  text: string;
  isActive: boolean;
}

export default function PostIdeasModal({ isOpen, onClose, onPostCreated }: PostIdeasModalProps) {
  const [additionalInstructions, setAdditionalInstructions] = useState('');
  const [ideas, setIdeas] = useState<PostIdea[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdea, setSelectedIdea] = useState<PostIdea | null>(null);
  const [showContentModal, setShowContentModal] = useState(false);
  const { user } = useAuth();
  const toast = useCustomToast();

  const handleGenerateIdeas = async () => {
    if (!user?.business_description) {
      toast.showErrorToast("Business description is required. Please set it in your client specifics.");
      return;
    }

    setLoading(true);
    try {
      const result = await generatePostIdeas(
        user.business_description,
        user.client_avatars ?? undefined,
        additionalInstructions
      );

      const newIdeas = result.ideas.map((idea: string, index: number) => ({
        id: `idea-${Date.now()}-${index}`,
        text: idea,
        isActive: true,
      }));

      setIdeas(newIdeas);
      toast.showSuccessToast(`Generated ${newIdeas.length} post ideas!`);
    } catch (error) {
      toast.showErrorToast("Failed to generate post ideas. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteIdea = (ideaId: string) => {
    setIdeas(prev => 
      prev.map(idea => 
        idea.id === ideaId 
          ? { ...idea, isActive: false }
          : idea
      ).sort((a, b) => {
        // Move inactive ideas to the end
        if (a.isActive && !b.isActive) return -1;
        if (!a.isActive && b.isActive) return 1;
        return 0;
      })
    );
  };

  const handleAcceptIdea = (idea: PostIdea) => {
    setSelectedIdea(idea);
    setShowContentModal(true);
  };

  const handlePostCreated = () => {
    setShowContentModal(false);
    setSelectedIdea(null);
    onPostCreated();
  };

  const activeIdeas = ideas.filter(idea => idea.isActive);

  return (
    <>
      <DialogRoot open={isOpen} onOpenChange={({ open }) => !open && onClose()}>
        <DialogContent>
          <DialogHeader>Generate Post Ideas</DialogHeader>
          <DialogBody>
            <VStack gap={4} alignItems="stretch">
              <Field label="Additional Instructions (Optional)">
                <Textarea
                  value={additionalInstructions}
                  onChange={(e) => setAdditionalInstructions(e.target.value)}
                  placeholder="Add any specific instructions or preferences for your post ideas..."
                  rows={3}
                />
              </Field>

              <Button
                onClick={handleGenerateIdeas}
                loading={loading}
                colorScheme="blue"
                size="lg"
              >
                GENERATE
              </Button>

              {ideas.length > 0 && (
                <Box>
                  <Text fontWeight="semibold" mb={3}>
                    Generated Ideas ({activeIdeas.length} active)
                  </Text>
                  <VStack gap={2} alignItems="stretch">
                    {ideas.map((idea) => (
                      <Box
                        key={idea.id}
                        p={3}
                        borderWidth={1}
                        borderRadius="md"
                        bg={idea.isActive ? "white" : "gray.50"}
                        opacity={idea.isActive ? 1 : 0.6}
                      >
                        <Text mb={2}>{idea.text}</Text>
                        <HStack justify="space-between">
                          <HStack>
                            {idea.isActive ? (
                              <Badge colorScheme="green">Active</Badge>
                            ) : (
                              <Badge colorScheme="gray">Deleted</Badge>
                            )}
                          </HStack>
                          {idea.isActive && (
                            <HStack>
                              <Button
                                size="sm"
                                variant="outline"
                                colorScheme="red"
                                onClick={() => handleDeleteIdea(idea.id)}
                              >
                                Delete
                              </Button>
                              <Button
                                size="sm"
                                colorScheme="blue"
                                onClick={() => handleAcceptIdea(idea)}
                              >
                                Accept
                              </Button>
                            </HStack>
                          )}
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                </Box>
              )}
            </VStack>
          </DialogBody>
          <DialogFooter>
            <DialogCloseTrigger asChild>
              <Button variant="subtle" colorPalette="gray">
                Close
              </Button>
            </DialogCloseTrigger>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>

      {selectedIdea && (
        <PostContentModal
          isOpen={showContentModal}
          onClose={() => setShowContentModal(false)}
          postIdea={selectedIdea}
          onPostCreated={handlePostCreated}
        />
      )}
    </>
  );
} 