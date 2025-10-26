import React, { useEffect, useState } from 'react';
import {
  Table,
  Image,
  Text,
  HStack,
  IconButton,
  Box,
  Spinner,
  Input,
  VStack,
} from '@chakra-ui/react';
import { getPostings, createPosting, updatePosting, deletePosting, uploadMedia } from '../../client/core/request';
import { UpcomingPostPublic, UpcomingPostCreate } from '../../client/types.gen';
import { FaFacebook, FaInstagram, FaTiktok } from 'react-icons/fa6';
import { FaPen, FaTrashAlt, FaPlus, FaLightbulb } from 'react-icons/fa';
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTrigger,
  DialogCloseTrigger,
} from '../../components/ui/dialog';
import { Field } from '../../components/ui/field';
import { Button } from '../../components/ui/button';
import useCustomToast from '../../hooks/useCustomToast';
import { createFileRoute } from "@tanstack/react-router";
import { addDays, format } from 'date-fns';
import PostIdeasModal from '../../components/PostIdeas/PostIdeasModal';

const defaultForm: Omit<UpcomingPostCreate, 'scheduled_time'> & { scheduled_time: string } = {
  media_url: '',
  text: '',
  hashtags: '',
  scheduled_time: format(addDays(new Date(), 1), "yyyy-MM-dd'T'HH:mm"),
  to_facebook: true,
  to_instagram: true,
  to_tiktok: true,
};

const SocialToggle = ({ icon, isChecked, onChange }: { icon: React.ReactNode, isChecked: boolean, onChange: () => void }) => (
  <IconButton
    aria-label="toggle social"
    colorScheme={isChecked ? 'blue' : 'gray'}
    variant={isChecked ? 'solid' : 'outline'}
    onClick={onChange}
    size="sm"
  >
    {icon}
  </IconButton>
);

const PostingsPage = () => {
  const [posts, setPosts] = useState<UpcomingPostPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [editId, setEditId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isIdeasModalOpen, setIsIdeasModalOpen] = useState(false);
  const toast = useCustomToast();
  const [filter, setFilter] = useState({ text: '', hashtag: '', facebook: true, instagram: true, tiktok: true });
  const [formError, setFormError] = useState<string | null>(null);
  const [fileUploading, setFileUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    setLoading(true);
    try {
      const res = await getPostings();
      setPosts(res.data);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id: string, field: 'to_facebook' | 'to_instagram' | 'to_tiktok', value: boolean) => {
    setUpdating(id);
    await updatePosting(id, { [field]: !value });
    setPosts(posts => posts.map(p => p.id === id ? { ...p, [field]: !value } : p));
    setUpdating(null);
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const validateForm = () => {
    if (!selectedFile) return 'Media is required.';
    if (!form.text.trim()) return 'Main text is required.';
    if (!form.scheduled_time) return 'Scheduled time is required.';
    if (new Date(form.scheduled_time) < new Date()) return 'Scheduled time must be in the future.';
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    if (!isImage && !isVideo) {
      setFormError('Only image or video files are allowed.');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    setFormError(null);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const error = validateForm();
    if (error) {
      setFormError(error);
      return;
    }
    setFormError(null);
    let mediaUrl;
    if (selectedFile) {
      setFileUploading(true);
      try {
        mediaUrl = await uploadMedia(selectedFile);
      } catch {
        setFormError('Failed to upload file.');
        setFileUploading(false);
        return;
      }
      setFileUploading(false);
    }
    try {
      const post = await createPosting({ ...form, media_url: mediaUrl, scheduled_time: new Date(form.scheduled_time).toISOString() });
      setPosts([post, ...posts]);
      setForm(defaultForm);
      setSelectedFile(null);
      setIsCreateOpen(false);
      toast.showSuccessToast('Posting created');
    } catch {
      toast.showErrorToast('Failed to create posting');
    }
  };

  const handleEdit = (post: UpcomingPostPublic) => {
    setEditId(post.id);
    setForm({
      media_url: post.media_url,
      text: post.text,
      hashtags: post.hashtags || '',
      scheduled_time: post.scheduled_time.slice(0, 16),
      to_facebook: post.to_facebook ?? true,
      to_instagram: post.to_instagram ?? true,
      to_tiktok: post.to_tiktok ?? true,
    });
    setIsEditOpen(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    const error = validateForm();
    if (error) {
      setFormError(error);
      return;
    }
    setFormError(null);
    let mediaUrl = form.media_url;
    if (selectedFile) {
      setFileUploading(true);
      try {
        mediaUrl = await uploadMedia(selectedFile);
      } catch {
        setFormError('Failed to upload file.');
        setFileUploading(false);
        return;
      }
      setFileUploading(false);
    }
    if (!editId) return;
    try {
      const updated = await updatePosting(editId, { ...form, media_url: mediaUrl, scheduled_time: new Date(form.scheduled_time).toISOString() });
      setPosts(posts => posts.map(p => p.id === editId ? updated : p));
      setEditId(null);
      setIsEditOpen(false);
      setSelectedFile(null);
      toast.showSuccessToast('Posting updated');
    } catch {
      toast.showErrorToast('Failed to update posting');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePosting(id);
      setPosts(posts => posts.filter(p => p.id !== id));
      toast.showSuccessToast('Posting deleted');
    } catch {
      toast.showErrorToast('Failed to delete posting');
    }
  };

  const filteredPosts = posts.filter(post =>
    post.text.toLowerCase().includes(filter.text.toLowerCase()) &&
    (filter.hashtag ? post.hashtags.toLowerCase().includes(filter.hashtag.toLowerCase()) : true) &&
    (filter.facebook ? post.to_facebook : true) &&
    (filter.instagram ? post.to_instagram : true) &&
    (filter.tiktok ? post.to_tiktok : true)
  );

  if (loading) return <Spinner size="xl" mt={10} />;

  return (
    <Box p={6}>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="2xl">Upcoming Postings</Text>
        <HStack gap={2}>
          <Button 
            colorScheme="purple" 
            onClick={() => setIsIdeasModalOpen(true)}
          >
            <FaLightbulb style={{ marginRight: 8 }} />
            Generate Ideas
          </Button>
          <DialogRoot open={isCreateOpen} onOpenChange={({ open }) => setIsCreateOpen(open)}>
            <DialogTrigger asChild>
              <Button colorScheme="blue" onClick={() => setForm(defaultForm)}><FaPlus style={{ marginRight: 8 }} />New Posting</Button>
            </DialogTrigger>
            <DialogContent>
              <form onSubmit={handleCreate}>
                <DialogHeader>New Posting</DialogHeader>
                <DialogBody>
                  <VStack gap={4} alignItems="stretch">
                    <Field required label="Media">
                      <Input type="file" accept="image/*,video/*" onChange={handleFileChange} disabled={fileUploading} />
                      {selectedFile && <Text fontSize="sm" color="gray.500">Selected: {selectedFile.name}</Text>}
                      {form.media_url && !selectedFile && (
                        form.media_url.match(/\.(mp4|webm|ogg)$/i)
                          ? <video src={form.media_url} width={80} height={80} controls style={{ borderRadius: 8, marginTop: 8 }} />
                          : <Image src={form.media_url} boxSize="80px" objectFit="cover" borderRadius={8} mt={2} />
                      )}
                    </Field>
                    {formError && <Text color="red.500">{formError}</Text>}
                    <Field required label="Main Text">
                      <Input name="text" value={form.text} onChange={handleInput} placeholder="Main text" />
                    </Field>
                    <Field label="Hashtags (comma separated)">
                      <Input name="hashtags" value={form.hashtags} onChange={handleInput} placeholder="tag1, tag2" />
                    </Field>
                    <Field required label="Scheduled Time">
                      <Input name="scheduled_time" type="datetime-local" value={form.scheduled_time} onChange={handleInput} />
                    </Field>
                    <HStack>
                      <SocialToggle icon={<FaFacebook />} isChecked={form.to_facebook} onChange={() => setForm(f => ({ ...f, to_facebook: !f.to_facebook }))} />
                      <SocialToggle icon={<FaInstagram />} isChecked={form.to_instagram} onChange={() => setForm(f => ({ ...f, to_instagram: !f.to_instagram }))} />
                      <SocialToggle icon={<FaTiktok />} isChecked={form.to_tiktok} onChange={() => setForm(f => ({ ...f, to_tiktok: !f.to_tiktok }))} />
                    </HStack>
                  </VStack>
                </DialogBody>
                <DialogFooter gap={2}>
                   {/* TODO: causes Warning: validateDOMNesting... */}
                  <DialogCloseTrigger asChild>
                    <Button variant="subtle" colorPalette="gray">Cancel</Button>
                  </DialogCloseTrigger>
                  <Button type="submit" colorScheme="blue">Create</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </DialogRoot>
        </HStack>
      </HStack>
      <HStack gap={4} alignItems="center" mb={4}>
        <Input placeholder="Filter by text" value={filter.text} onChange={e => setFilter(f => ({ ...f, text: e.target.value }))} maxW="200px" />
        <Input placeholder="Filter by hashtag" value={filter.hashtag} onChange={e => setFilter(f => ({ ...f, hashtag: e.target.value }))} maxW="200px" />
        <HStack>
          <SocialToggle icon={<FaFacebook />} isChecked={filter.facebook} onChange={() => setFilter(f => ({ ...f, facebook: !f.facebook }))} />
          <SocialToggle icon={<FaInstagram />} isChecked={filter.instagram} onChange={() => setFilter(f => ({ ...f, instagram: !f.instagram }))} />
          <SocialToggle icon={<FaTiktok />} isChecked={filter.tiktok} onChange={() => setFilter(f => ({ ...f, tiktok: !f.tiktok }))} />
        </HStack>
      </HStack>
      <Table.Root size={{ base: 'sm', md: 'md' }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="sm">Media</Table.ColumnHeader>
            <Table.ColumnHeader w="md">Main Text</Table.ColumnHeader>
            <Table.ColumnHeader w="md">Hashtags</Table.ColumnHeader>
            <Table.ColumnHeader w="md">Socials</Table.ColumnHeader>
            <Table.ColumnHeader w="md">Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {filteredPosts.map(post => (
            <Table.Row key={post.id}>
              <Table.Cell>
                {post.media_url.match(/\.(mp4|webm|ogg)$/i)
                  ? <video src={post.media_url} width={80} height={80} controls style={{ borderRadius: 8 }} />
                  : <Image src={post.media_url} boxSize="80px" objectFit="cover" borderRadius={8} />}
              </Table.Cell>
              <Table.Cell>{post.text}</Table.Cell>
              <Table.Cell>{post.hashtags?.split(',').map(tag => <Text as="span" key={tag} color="gray.500" mr={1}>#{tag.trim()}</Text>) || ''}</Table.Cell>
              <Table.Cell>
                <HStack gap={2}>
                  <SocialToggle
                    icon={<FaFacebook />}
                    isChecked={post.to_facebook ?? true}
                    onChange={() => handleToggle(post.id, 'to_facebook', post.to_facebook ?? true)}
                  />
                  <SocialToggle
                    icon={<FaInstagram />}
                    isChecked={post.to_instagram ?? true}
                    onChange={() => handleToggle(post.id, 'to_instagram', post.to_instagram ?? true)}
                  />
                  <SocialToggle
                    icon={<FaTiktok />}
                    isChecked={post.to_tiktok ?? true}
                    onChange={() => handleToggle(post.id, 'to_tiktok', post.to_tiktok ?? true)}
                  />
                  {updating === post.id && <Spinner size="sm" />}
                </HStack>
              </Table.Cell>
              <Table.Cell>
                <HStack spacing={2}>
                  <IconButton aria-label="Edit" size="sm" colorScheme="yellow" variant="outline" onClick={() => handleEdit(post)}><FaPen /></IconButton>
                  <IconButton aria-label="Delete" size="sm" colorScheme="red" variant="outline" onClick={() => handleDelete(post.id)}><FaTrashAlt /></IconButton>
                </HStack>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <DialogRoot open={isEditOpen} onOpenChange={({ open }) => { setIsEditOpen(open); if (!open) setEditId(null); }}>
        <DialogContent>
          <form onSubmit={handleUpdate}>
            <DialogHeader>Edit Posting</DialogHeader>
            <DialogBody>
              <VStack gap={4} alignItems="stretch">
                <Field required label="Media">
                  <Input type="file" accept="image/*,video/*" onChange={handleFileChange} disabled={fileUploading} />
                  {selectedFile && <Text fontSize="sm" color="gray.500">Selected: {selectedFile.name}</Text>}
                  {form.media_url && !selectedFile && (
                    form.media_url.match(/\.(mp4|webm|ogg)$/i)
                      ? <video src={form.media_url} width={80} height={80} controls style={{ borderRadius: 8, marginTop: 8 }} />
                      : <Image src={form.media_url} boxSize="80px" objectFit="cover" borderRadius={8} mt={2} />
                  )}
                </Field>
                {formError && <Text color="red.500">{formError}</Text>}
                <Field required label="Main Text">
                  <Input name="text" value={form.text} onChange={handleInput} placeholder="Main text" />
                </Field>
                <Field label="Hashtags (comma separated)">
                  <Input name="hashtags" value={form.hashtags} onChange={handleInput} placeholder="tag1, tag2" />
                </Field>
                <Field required label="Scheduled Time">
                  <Input name="scheduled_time" type="datetime-local" value={form.scheduled_time} onChange={handleInput} />
                </Field>
                <HStack>
                  <SocialToggle icon={<FaFacebook />} isChecked={form.to_facebook} onChange={() => setForm(f => ({ ...f, to_facebook: !f.to_facebook }))} />
                  <SocialToggle icon={<FaInstagram />} isChecked={form.to_instagram} onChange={() => setForm(f => ({ ...f, to_instagram: !f.to_instagram }))} />
                  <SocialToggle icon={<FaTiktok />} isChecked={form.to_tiktok} onChange={() => setForm(f => ({ ...f, to_tiktok: !f.to_tiktok }))} />
                </HStack>
              </VStack>
            </DialogBody>
            <DialogFooter gap={2}>
              <DialogCloseTrigger asChild>
                <Button variant="subtle" colorPalette="gray">Cancel</Button>
              </DialogCloseTrigger>
              <Button type="submit" colorScheme="blue">Save</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </DialogRoot>

      <PostIdeasModal
        isOpen={isIdeasModalOpen}
        onClose={() => setIsIdeasModalOpen(false)}
        onPostCreated={() => {
          setIsIdeasModalOpen(false);
          fetchPosts();
        }}
      />
    </Box>
  );
};

export const Route = createFileRoute("/_layout/postings")({
  component: PostingsPage,
}); 